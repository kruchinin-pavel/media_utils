#!/usr/bin/python3.6
import os
import shutil
import sys
import time
from os.path import splitext
from typing import Tuple

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
            value: str = exif['DateTimeOriginal']
            dt, tm = [v.split(':') for v in value.split(' ')]
            return f'{dt[0]}/{dt[1]}', f'{"".join(dt + tm)}'
    elif extension.lower() in (".mp4", ".mp3", ".mov", ".mkv"):
        ctime = time.localtime(os.path.getmtime(f))
        return time.strftime(PATH_FMT, ctime), time.strftime(PREFIX_FMT, ctime)
    return None, None


def process_file(f):
    if os.path.isfile(f):
        path = os.path.dirname(f)
        subpath, timestamp = get_timestamp(f)
        if timestamp is None:
            print("File %s not processed" % f)
            return
        prefix = "%s_" % timestamp
        basename = os.path.basename(f)
        if basename[0:len(prefix)] == prefix:
            print("File %s was already renamed, just moving" % (f))
            nn = os.path.join(path, subpath, basename)
        else:
            nn = os.path.join(path, subpath, "%s%s" % (prefix, basename))
        if not os.path.isdir(os.path.dirname(nn)):
            os.makedirs(os.path.dirname(nn))
        shutil.move(f, nn)
        print("File %s renamed to %s" % (f, nn))
    else:
        for _f in os.listdir(f):
            full_name = os.path.join(f, _f)
            if os.path.isdir(full_name):
                continue
            process_file(full_name)


def main(paths):
    for f in paths:
        process_file(f)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        print("Usage: %s <JPG files with Exif tags>" % (sys.argv[0]))
