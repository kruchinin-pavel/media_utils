#!/usr/bin/python3.6
import filecmp
import os
import shutil
import sys
import time
from os.path import splitext
from typing import Tuple, List

PREFIX_FMT = '%Y%m%d%H%M%S'
PATH_FMT = '%Y/%m'


def get_timestamp(f) -> Tuple[str, str]:
    from PIL import Image, ExifTags
    file_name, extension = splitext(f)
    if extension.lower() in (".jpg", ".jpeg"):
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
            return f'{dt[0]}/{dt[1]}', f'{"".join(dt + tm)}'
    elif extension.lower() in (".mp4", ".mp3", ".mov", ".mkv"):
        ctime = time.localtime(os.path.getmtime(f))
        return time.strftime(PATH_FMT, ctime), time.strftime(PREFIX_FMT, ctime)
    raise ValueError(f'Unsupported file {f}')


def move_file(lst: List[Tuple[str, str]], dump_only=False):
    for from_file, to_file in lst:
        if os.path.isfile(to_file) and not filecmp.cmp(from_file, to_file):
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
        basename = os.path.basename(f)
        try:
            subpath, timestamp = get_timestamp(f)
            prefix = "%s_" % timestamp
            if basename[0:len(prefix)] == prefix:
                print("File %s was already renamed, just moving" % (f))
                nn = os.path.join(root, subpath, basename)
            else:
                nn = os.path.join(root, subpath, "%s%s" % (prefix, basename))
        except ValueError as ve:
            print("File %s not processed" % f)
            nn = os.path.join(root, 'skipped', basename)
        if f == nn:
            return []
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
        main(sys.argv[1:])
    else:
        print("Usage: %s <JPG files with Exif tags>" % (sys.argv[0]))
