#!/usr/bin/python3.6
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

import PIL
import pywintypes
import regex
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


def get_exif_creation_dates_video(path) -> datetime:
    # https://exiftool.org/index.html
    EXIFTOOL_DATE_TAG_VIDEOS = "Create Date"
    exe = os.path.join(os.getcwd(), 'utils/exiftool.exe')
    process: subprocess.CompletedProcess = subprocess.run([exe, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not process.returncode == 0:
        raise RuntimeError('Error running exiftool')
    lines = process.stdout.decode("cp1251").replace("\r", "").split("\n")
    for l in lines:
        if EXIFTOOL_DATE_TAG_VIDEOS in l:
            arr = [int(s.strip()) for s in regex.split(":+|\s+", l[l.index(':') + 1:].strip())]
            if arr[0] == 0:
                return None
            return datetime(arr[0], arr[1], arr[2], arr[3], arr[4])
    return None


class Diff:

    def __init__(self, source_file_name: str, dest_file_name: Optional[str],
                 new_date_time_attribute: Optional[datetime], ctime: Optional[datetime]):
        super().__init__()
        self.ctime = ctime
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
        if os.path.isfile(self.dest_file_name) and not filecmp.cmp(self.dest_file_name,
                                                                   self.dest_file_name) and os.path.getsize(
            self.dest_file_name) > os.path.getsize(self.source_file_name):
            raise ValueError(f'ABORT: Same names but diff files from {self.source_file_name} to {self.dest_file_name}')

        to_dir = os.path.dirname(self.dest_file_name)
        print(f'{"dryRun" if dryRun else ""}File {self.source_file_name} renamed to {self.dest_file_name}')
        if not dryRun:
            if not os.path.isdir(to_dir):
                os.makedirs(to_dir)
            shutil.move(self.source_file_name, self.dest_file_name)


def is_vdeo(extension: str) -> bool:
    return extension.lower() in (".mp4", ".mp3", ".mov", ".mkv", ".3gp", ".avi", ".m4v")


def get_timestampe_from_name(f: str) -> datetime:
    try:
        f = re.sub("[^0-9.]", '', f);
        d = [int(c) for c in [f[0:4], f[4:6], f[6:8], f[8:10], f[10:12], f[12:14]]]
        return datetime(d[0], d[1], d[2], d[3], d[4], d[5])
    except:
        return None


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
    if extension.lower() in (".jpg", ".jpeg", ".png"):
        try:
            img = Image.open(f)
            exif_obj = img._getexif()
            value = None
            if exif_obj is not None:
                exif = {ExifTags.TAGS[k]: v for k, v in exif_obj.items() if k in ExifTags.TAGS}
                value: str = exif.get('DateTimeOriginal', None)
                if value is None:
                    value = exif.get('DateTime', None)
            if value is None:
                dt = get_timestampe_from_name(os.path.basename(f))
                if dt is None:
                    raise ValueError(f'in {f} neither DateTimeOriginal nor DateTime found. Has only: {exif.keys()}')
                else:
                    return datetime.strftime(dt, PATH_FMT), datetime.strftime(dt, PREFIX_FMT), False
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
            # properties = propsys.SHGetPropertyStoreFromParsingName(f)
            # dt = properties.GetValue(pscon.PKEY_Media_DateEncoded).GetValue()
            dt = get_exif_creation_dates_video(f)
            if dt is not None:
                ctime = dt
            elif pickup_timestamps:
                dt = get_timestampe_from_name(fn)
                if dt is not None:
                    ctime = dt
                else:
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
        if do_move:
            diff.move_if_needed(dryRun)
        else:
            diff.dest_file_name = diff.source_file_name
        diff.ctime_update_if_different(dryRun)


def process_file_list(sortedfiles, f, root, pickup_timestamps=True, do_move=False):
    lst: List[Diff] = []
    for _f in sortedfiles:
        increment: List[Diff] = process_file(os.path.join(f, _f), root, pickup_timestamps,
                                             lst[-1].ctime if len(lst) > 0 else None)
        move_file(increment, False, do_move=do_move)
        lst.extend(increment)


futures = []


def process_file(f, root=None, pickup_timestamps=True, lastctime: datetime = None, exec=None, do_move=False) -> List[
    Diff]:
    if root is None:
        root = f
    if os.path.isfile(f):
        if os.stat(f).st_size == 0:
            print("File %s of zero size, ignoring" % f)
            return []
        if f'{os.path.relpath(f, root)}'.startswith('skipped'):
            return []
        basename = os.path.basename(f)
        ctime = None
        try:
            new_datetime = None
            subpath, timestamp, change_filename = get_timestamp(f, lastctime=lastctime)
            prefix = "%s_" % timestamp
            ctime: datetime = datetime.fromtimestamp(time.mktime(time.localtime(os.path.getmtime(f))))
            ftime: datetime = dateparser.parse(timestamp, date_formats=['%Y%m%d%H%M%S'])
            if ftime is not None and (
                    ctime.year != ftime.year or ctime.month != ftime.month or ctime.hour != ftime.hour or ctime.min != ftime.min):
                print(f'Need to update this {f} with new date: {ftime} before it was {ctime}')
                new_datetime = ftime
            if basename[0:len(prefix)] == prefix:
                nn = os.path.join(root, subpath, basename)
                # print("File %s was already renamed, just moving" % f)
                return [Diff(f, nn, new_datetime, ctime)]
            elif change_filename:
                nn = os.path.join(root, subpath, "%s%s" % (prefix, basename))
            else:
                nn = os.path.join(root, subpath, "%s" % (basename))
        except ValueError as ve:
            print(f"File {f} not processed: {ve}")
            nn = os.path.join(root, 'skipped', basename)
        return [Diff(f, nn, new_date_time_attribute=new_datetime, ctime=ctime)]
    else:
        sortedfiles = sorted(os.listdir(f))
        lst: List[Diff] = []
        files = []
        for fi in sortedfiles:
            if os.path.isfile(f + "/" + fi):
                files.append(fi)
        if len(files) > 0:
            if exec is not None:
                while len(futures) > 5:
                    fut = futures[0]
                    fut.result()
                    futures.remove(fut)
                print(f"Queueing {len(files)} files from {f}")
                future = exec.submit(process_file_list, files, f, root, pickup_timestamps, do_move)
                futures.append(future)
            else:
                process_file_list(files, f, root, pickup_timestamps, do_move=do_move)
        for _f in (fi for fi in sortedfiles if os.path.isdir(f + "/" + fi)):
            process_file(os.path.join(f, _f), root, pickup_timestamps,
                         lst[-1].new_date_time_attribute if len(lst) > 0 else None, exec=exec, do_move=do_move)
        return []


def main(paths, root=None, do_move=False):
    with ThreadPoolExecutor(max_workers=5) as executor:
        for f in paths:
            lst: List[Diff] = []
            lst.extend(process_file(f, root=root, exec=executor, do_move=do_move))
            move_file(lst, False, do_move=do_move)
        for future in futures:
            print('Waiting task completion on the end')
            future.result()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # for dir_to_look in sys.argv[1:]:
        #     if not os.path.isdir(dir_to_look):
        #         raise AttributeError(f'Not a directory: {dir_to_look}')
        print(f'Looking at {sys.argv[1:]}')
        main(sys.argv[1:])
    else:
        print("Usage: %s <JPG files with Exif tags>" % (sys.argv[0]))
