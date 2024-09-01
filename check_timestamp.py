from os.path import splitext
from media_process import process_file
import sys
import os


def main(paths):
    lst = []
    for f in paths:
        lst.extend(process_file(f, pickup_timestamps=False))
    print(lst)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for dir_to_look in sys.argv[1:]:
            if not os.path.isdir(dir_to_look):
                raise AttributeError(f'Not a directory: {dir_to_look}')
        print(f'Looking at {sys.argv[1:]}')
        main(sys.argv[1:])
    else:
        print("Usage: %s <JPG files with Exif tags>" % (sys.argv[0]))
