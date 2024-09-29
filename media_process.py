#!/usr/bin/python3.6
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, Future

import regex
import datetime
from datetime import datetime
import os
import sys
import time
from os.path import splitext, normpath
from pathlib import Path
from typing import Tuple, List, Optional

import dateparser

PREFIX_FMT = '%Y%m%d%H%M%S'
PATH_FMT = '%Y/%m'


def get_exif_creation_dates_video(path) -> datetime:
    # https://exiftool.org/index.html
    EXIFTOOL_DATE_TAG_VIDEOS = "Create Date"
    exe = os.path.join(os.getcwd(), 'utils/exiftool.exe') if os.name == 'nt' else 'exiftool'
    cp = "cp1251" if os.name == 'nt' else 'utf-8'
    process: subprocess.CompletedProcess = subprocess.run([exe, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not process.returncode == 0:
        raise RuntimeError('Error running exiftool')
    lines = process.stdout.decode(cp).replace("\r", "").split("\n")
    for l in lines:
        if EXIFTOOL_DATE_TAG_VIDEOS in l:
            arr = [int(s.strip()) for s in regex.split(":+|\\s+", l[l.index(':') + 1:].strip())]
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

    def _need_move(self) -> bool:
        return Path(self.source_file_name) != Path(self.dest_file_name)

    def apply(self, do_move=True) -> str:
        cmd = ""
        to_dir = os.path.dirname(self.dest_file_name)
        replaces = normpath(self.source_file_name)
        replaced = normpath(self.dest_file_name)
        if self.new_date_time_attribute is not None:
            cmd += f"touch \"{replaces}\" -d \"{self.new_date_time_attribute.strftime('%Y-%m-%d %H:%M:%S')}\"\n".replace(
                "\\", "/")
        if do_move and self._need_move():
            if not os.path.isdir(to_dir):
                replace = normpath(to_dir)
                cmd += f'mkdir "{replace}"\n'
            # os.makedirs(to_dir)
            cmd += f'mv "{replaces}" "{replaced}"\n'
            # shutil.move(self.source_file_name, self.dest_file_name)
        return cmd


class BadDiff(Diff):
    def __init__(self, source_file_name: str):
        Diff.__init__(self, source_file_name, dest_file_name=None, new_date_time_attribute=None, ctime=None)

    def apply(self, do_move=True) -> str:
        replace = self.source_file_name.replace('/', '\\')
        return f"rm \"{replace}\""


def get_timestampe_from_name(f_: str) -> datetime:
    try:
        f = Path(f_).name
        f = "".join(filter(str.isdigit, f))
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
    file_name, extension = splitext(f)
    if extension.lower() in (".jpg", ".jpeg", ".png", ".mp4", ".mp3", ".mov", ".mkv", ".3gp", ".avi", ".m4v"):
        try:
            dt = get_exif_creation_dates_video(f)
        except Exception:
            return "exception", "", False
    else:
        return "unprocessed", "", False
    if dt is not None:
        ctime = dt
    elif pickup_timestamps:
        dt = get_timestampe_from_name(f)
        if dt is not None:
            ctime = dt
        else:
            ctime = datetime.fromtimestamp(time.mktime(time.localtime(os.path.getmtime(f))))
            year_mo = get_year_mo_from_path(Path(file_name))
            if (year_mo[0] > 0 and ctime.year != year_mo[0]) or (year_mo[1] > 0 and ctime.month != year_mo[1]):
                ctime = ctime.replace(year=year_mo[0], month=year_mo[1])
            elif lastctime is not None:
                ctime = datetime(int(lastctime[0:4]), int(lastctime[4:6]), int(lastctime[6:8]), int(lastctime[8:10]),
                                 int(lastctime[10:12]), int(lastctime[12:14]))
    return datetime.strftime(ctime, PATH_FMT), datetime.strftime(ctime, PREFIX_FMT), False


def process_file_list(sortedfiles, f, root, pickup_timestamps) -> List[Diff]:
    lst: List[Diff] = []
    for _f in sortedfiles:
        # print(f"Processing {_f}")
        increment: List[Diff] = process_file(os.path.join(f, _f), root, pickup_timestamps,
                                             lst[-1].ctime if len(lst) > 0 else None)
        lst.extend(increment)
    print(f"Done {len(lst)} files from {f}")
    return lst


futures: List[Future] = []


def process_file(f, root=None, pickup_timestamps=True, lastctime: datetime = None, exec=None) -> List[
    Diff]:
    if root is None:
        root = f
    try:
        if os.path.isfile(f):
            if os.stat(f).st_size == 0:
                print(f"File %s of zero size, ignoring >>{f}")
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
                    # print(f'Need to update this {f} with new date: {ftime} before it was {ctime}')
                    new_datetime = ftime
                    ctime = new_datetime
                if basename[0:len(prefix)] == prefix:
                    nn = os.path.join(root, subpath, basename)
                    return [Diff(f, nn, new_datetime, ctime)]
                elif change_filename:
                    nn = os.path.join(root, subpath, "%s%s" % (prefix, basename))
                else:
                    nn = os.path.join(root, subpath, "%s" % (basename))
            except ValueError as ve:
                # print(f"File {f} not processed: {ve}")
                # nn = os.path.join(root, 'skipped', basename)
                return [BadDiff(f)]
            return [Diff(f, nn, new_date_time_attribute=new_datetime, ctime=timestamp)]
        else:
            sortedfiles = sorted(os.listdir(f))
            lst: List[Diff] = []
            files = []
            for fi in sortedfiles:
                if os.path.isfile(f + "/" + fi):
                    files.append(fi)
            if len(files) > 0:
                if exec is not None:
                    print(f"Queueing {len(files)} files from {f}. Tasks awaiting {len(futures)}")
                    futures.append(exec.submit(process_file_list, files, f, root, pickup_timestamps))
                else:
                    lst.extend(process_file_list(files, f, root, pickup_timestamps))
            for _f in (fi for fi in sortedfiles if os.path.isdir(f + "/" + fi)):
                process_file(os.path.join(f, _f), root, pickup_timestamps,
                             lst[-1].new_date_time_attribute if len(lst) > 0 else None, exec=exec)
            return lst
    except Exception as e:
        logging.error(f"Exception with {f}: {e}", e)
        raise e


def main(paths, root=None, do_move=False):
    with open("cmd.bat", "a") as out:
        out.writelines(f":Starting new {datetime.now()}\n")

    with ThreadPoolExecutor(max_workers=5) as executor:
        for f in paths:
            lst = process_file(f, root=root, exec=executor)
            with open("cmd.bat", "a") as out:
                for diff in lst:
                    for str in diff.apply(do_move=do_move).split("\n"):
                        if len(str) > 0:
                            out.write(f'{str}\n')
        while len(futures) > 0:
            for future in futures:
                if future.running():
                    continue
                diffs = future.result()
                print(f'One task printed: {len(diffs)} commands. Tasks awaiting: {len(futures)}')
                with open("cmd.bat", "a") as out:
                    for diff in diffs:
                        for str in diff.apply(do_move=do_move).split("\n"):
                            if len(str) > 0:
                                out.write(f'{str}\n')
                futures.remove(future)
                break
            time.sleep(3)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # for dir_to_look in sys.argv[1:]:
        #     if not os.path.isdir(dir_to_look):
        #         raise AttributeError(f'Not a directory: {dir_to_look}')
        print(f'Looking at {sys.argv[1:]}')
        main(sys.argv[1:],
             # main(["//pi.local/black/photo_vania"],
             # root='//pi.local/black/photo_vania',
             do_move=True)
    else:
        print("Usage: %s <JPG files with Exif tags>" % (sys.argv[0]))
