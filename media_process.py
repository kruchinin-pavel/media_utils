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
from typing import Tuple, List, Optional

import dateparser

PREFIX_FMT = '%Y%m%d%H%M%S'
PATH_FMT = '%Y/%m'


class Diff:

    def __init__(self, source_file_name: str, dest_file_name: Optional[str],
                 new_date_time_attribute: Optional[datetime]):
        super().__init__()
        self.new_date_time_attribute = new_date_time_attribute
        self.dest_file_name = dest_file_name
        self.source_file_name = source_file_name

    def __str__(self) -> str:
        return f'{self.source_file_name},{self.dest_file_name},{None if self.new_date_time_attribute is None else self.new_date_time_attribute}'

    def ctime_update_if_different(self, dryRun=True) -> bool:
        if self.new_date_time_attribute is not None:
            print(
                f'{"dryRun" if dryRun else ""}Changing timestamp: {self.dest_file_name} to {self.new_date_time_attribute}')
            if not dryRun:
                os.utime(self.dest_file_name,
                         times=((self.new_date_time_attribute - datetime(1970, 1, 1)).total_seconds(),
                                (self.new_date_time_attribute - datetime(1970, 1, 1)).total_seconds()))
            return True
        return False

    def need_move(self) -> bool:
        return Path(self.source_file_name) != Path(self.dest_file_name)

    def move_if_needed(self, dryRun=True) -> bool:
        if not self.need_move():
            return False
        to_dir = os.path.dirname(self.dest_file_name)
        print(f'{"dryRun" if dryRun else ""}File {self.source_file_name} renamed to {self.dest_file_name}')
        if not dryRun:
            if not os.path.isdir(to_dir):
                os.makedirs(to_dir)
            shutil.move(self.source_file_name, self.dest_file_name)


def is_vdeo(extension: str) -> bool:
    return extension.lower() in (".mp4", ".mp3", ".mov", ".mkv", ".3gp", ".avi", ".m4v")


def get_year_mo_from_path(path: Path) -> Tuple[int, int]:
    try:
        year = int(path.parent.parent.name)
        month = int(path.parent.name)
        return [year, month]
    except:
        return [0, 0]


def get_timestamp(f, pickup_timestamps=True, lastctime: datetime = None) -> Tuple[str, str, bool]:
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
                return f'{dt[0]}{os.sep}{dt[1]}', f'{"".join(dt + tm)}', False
        except PIL.UnidentifiedImageError as e:
            raise ValueError(f'Error opening {file_name}: {e}', e)
        except OSError as e:
            raise ValueError(f'Error opening {file_name}: {e}', e)
    elif is_vdeo(extension):
        try:
            fn = Path(file_name).name
            fn = "".join(filter(str.isdigit, fn))
            change_file_name = False
            properties = propsys.SHGetPropertyStoreFromParsingName(f)
            dt = properties.GetValue(pscon.PKEY_Media_DateEncoded).GetValue()
            if dt is not None and 0 < (datetime.now() - dt.replace(tzinfo=None)).days < 5 * 365:
                ctime = dt
            elif pickup_timestamps:
                year_mo = get_year_mo_from_path(Path(file_name))
                ctime = datetime.fromtimestamp(time.mktime(time.localtime(os.path.getmtime(f))))
                if year_mo[0] > 0 and ctime.year != year_mo[0] and year_mo[1] > 0 and ctime.month != year_mo[1]:
                    ctime = ctime.replace(year=year_mo[0], month=year_mo[1])
                    if lastctime is not None:
                        ctime = lastctime
                    print(f"Customized date for file {f} to: {ctime}")
                else:
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


def move_file(lst: List[Diff], dryRun=True, do_move=True):
    for diff in lst:
        from_file = diff.source_file_name
        to_file = diff.dest_file_name
        if os.path.isfile(to_file) and not filecmp.cmp(from_file, to_file) and os.path.getsize(
                to_file) > os.path.getsize(from_file):
            raise ValueError(f'ABORT: Same names but diff files from {from_file} to {to_file}')

    for diff in lst:
        if do_move:
            diff.move_if_needed(dryRun)
        else:
            diff.dest_file_name = diff.source_file_name
        diff.ctime_update_if_different(dryRun)


def process_file(f, root=None, pickup_timestamps=True, lastctime: datetime = None) -> List[Diff]:
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
            new_datetime = None
            subpath, timestamp, change_filename = get_timestamp(f, lastctime=lastctime)
            prefix = "%s_" % timestamp
            ctime: datetime = datetime.fromtimestamp(time.mktime(time.localtime(os.path.getmtime(f))))
            ftime: datetime = dateparser.parse(timestamp, date_formats=['%Y%m%d%H%M%S'])
            if ctime.year != ftime.year and ctime.month != ftime.month:
                print(f'Need to update this {f} with new date: {ftime} before it was {ctime}')
                new_datetime = ftime
            if basename[0:len(prefix)] == prefix:
                nn = os.path.join(root, subpath, basename)
                print("File %s was already renamed, just moving" % f)
                return [Diff(f, nn, new_datetime)]
            elif change_filename:
                nn = os.path.join(root, subpath, "%s%s" % (prefix, basename))
            else:
                nn = os.path.join(root, subpath, "%s" % (basename))
        except ValueError as ve:
            print("File %s not processed" % f)
            nn = os.path.join(root, 'skipped', basename)
        return [Diff(f, nn, new_datetime)]
    else:
        lst: List[Diff] = []
        sortedfiles = sorted(os.listdir(f))
        for _f in sortedfiles:
            lst.extend(process_file(os.path.join(f, _f), root, pickup_timestamps,
                                    lst[-1].new_date_time_attribute if len(lst) > 0 else None))
        return lst


def main(paths, root=None):
    for f in paths:
        lst: List[Diff] = []
        lst.extend(process_file(f, root=root))
        move_file(lst, False, do_move=False)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # for dir_to_look in sys.argv[1:]:
        #     if not os.path.isdir(dir_to_look):
        #         raise AttributeError(f'Not a directory: {dir_to_look}')
        print(f'Looking at {sys.argv[1:]}')
        main(sys.argv[1:])
    else:
        print("Usage: %s <JPG files with Exif tags>" % (sys.argv[0]))
