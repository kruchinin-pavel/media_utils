#!/usr/bin/python3.6
import PIL
import pywintypes
from win32com.propsys import propsys, pscon
import datetime
from datetime import datetime
import filecmp
import os
import shutil
import sys
import time
from os.path import splitext
from pathlib import Path
from typing import Tuple, List

import dateparser

PREFIX_FMT = '%Y%m%d%H%M%S'
PATH_FMT = '%Y/%m'


def get_timestamp(f) -> Tuple[str, str, bool]:
    from PIL import Image, ExifTags
    file_name, extension = splitext(f)
    if extension.lower() in (".jpg", ".jpeg"):
        try:
            img = Image.open(f)
            exif_obj = img._getexif()
            if exif_obj is not None:
                exif = {ExifTags.TAGS[k]: v for k, v in exif_obj.items() if k in ExifTags.TAGS}
                value: str = exif.get('DateTimeOriginal', None)
                if value is None:
                    value = exif.get('DateTime', None)
                    if value is None:
                        raise ValueError(f'in {f} neither DateTimeOriginal nor DateTime found. Has only: {exif.keys()}')
                dt, tm = [v.split(':') for v in value.split(' ')]
                return f'{dt[0]}{os.sep}{dt[1]}', f'{"".join(dt + tm)}', True
        except PIL.UnidentifiedImageError as e:
            raise ValueError(f'Error opening {file_name}: {e}', e)
    elif extension.lower() in (".mp4", ".mp3", ".mov", ".mkv", ".3gp"):
        try:
            fn = Path(file_name).name
            fn = "".join(filter(str.isdigit, fn))
            change_file_name = True
            properties = propsys.SHGetPropertyStoreFromParsingName(f)
            dt = properties.GetValue(pscon.PKEY_Media_DateEncoded).GetValue()
            if dt is not None and 0 < (datetime.now() - dt.replace(tzinfo=None)).days < 5 * 365:
                ctime = dt
            else:
                ctime = datetime.fromtimestamp(time.mktime(time.localtime(os.path.getmtime(f))))
                dt: datetime = dateparser.parse(fn, date_formats=['%Y%m%d%H%M%S'])
                if dt is not None and 0 < (datetime.now() - dt).days < 5 * 365 and dt < ctime:
                    ctime = dt
                    change_file_name = False
            return datetime.strftime(ctime, PATH_FMT), datetime.strftime(ctime, PREFIX_FMT), change_file_name
        except pywintypes.com_error as com_err:
            raise ValueError(f'COM error with {file_name}: {com_err}', com_err)
        except Exception as e:
            raise e
    raise ValueError(f'Unsupported file {f}')


def move_file(lst: List[Tuple[str, str]], dump_only=False):
    for from_file, to_file in lst:
        if os.path.isfile(to_file) and not filecmp.cmp(from_file, to_file) and os.path.getsize(
                to_file) > os.path.getsize(from_file):
            raise ValueError(f'ABORT: Same names but diff files from {from_file} to {to_file}')

    for from_file, to_file in lst:
        to_dir = os.path.dirname(to_file)
        print(f'File {from_file} renamed to {to_file}')
        if not dump_only:
            if not os.path.isdir(to_dir):
                os.makedirs(to_dir)
            shutil.move(from_file, to_file)


def process_file(f, root=None) -> List[Tuple[str, str]]:
    if root is None:
        root = f
    if os.path.isfile(f):
        if os.stat(f).st_size == 0:
            print("File %s of zero size, ignoring" % f)
            return []
        if f'{os.path.relpath(f, root)}'.startswith('skipped'):
            return []
        basename = os.path.basename(f)
        try:
            subpath, timestamp, change_filename = get_timestamp(f)
            prefix = "%s_" % timestamp
            if basename[0:len(prefix)] == prefix:
                nn = os.path.join(root, subpath, basename)
                if f == nn:
                    return []
                print("File %s was already renamed, just moving" % f)
            elif change_filename:
                nn = os.path.join(root, subpath, "%s%s" % (prefix, basename))
            else:
                nn = os.path.join(root, subpath, "%s" % (basename))
        except ValueError as ve:
            print("File %s not processed" % f)
            nn = os.path.join(root, 'skipped', basename)
        return [[f, nn]]
    else:
        lst = []
        for _f in os.listdir(f):
            lst.extend(process_file(os.path.join(f, _f), root))
        return lst


def main(paths):
    lst = []
    for f in paths:
        lst.extend(process_file(f))
    move_file(lst)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for dir_to_look in sys.argv[1:]:
            if not os.path.isdir(dir_to_look):
                raise AttributeError(f'Not a directory: {dir_to_look}')
        print(f'Looking at {sys.argv[1:]}')
        main(sys.argv[1:])
    else:
        print("Usage: %s <JPG files with Exif tags>" % (sys.argv[0]))
