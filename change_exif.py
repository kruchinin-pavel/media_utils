import os

import regex
from PIL import Image, ExifTags


def main():
    d = '//pi.local/black/videos/photo_bkp/2016/03'
    for f in os.listdir(d):
        process_file(d, f)
    # process_file('D:/tmp', '19820303171517_1982-03-03-0408(0).jpg')


def process_file(d, f):
    if not f.endswith("jpg"):
        return
    import piexif
    img = Image.open(d + '/' + f)
    tags = {v: k for k, v in ExifTags.TAGS.items()}
    exif_dict = piexif.load(img.info['exif'])
    dtb = exif_dict['0th'][tags['DateTime']].decode("utf-8")
    dts = [int(v) for v in regex.split("\:|\s", dtb)]
    if dts[0] == 1982:
        exif_dict['0th'][tags['DateTime']] = '2016:03:15 15:00'.encode("utf-8")
        exif_bytes = piexif.dump(exif_dict)
        img.save(d + "/" + f, "jpeg", exif=exif_bytes)
        print(f'{f}')


if __name__ == '__main__':
    main()
