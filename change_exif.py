import regex
from PIL import Image, ExifTags
import os
from media_process import get_timestamp_from_name


def main():
    d = 'D:/users/krucpav/photo/pavel/Ulefone'
    for f in os.listdir(d):
        process_file(d, f)
    # process_file(d, 'IMG_20191124_114930_7.jpg')


def process_file(d, f):
    if not f.lower().endswith("jpg"):
        return
    import piexif
    img = Image.open(d + '/' + f)
    tags = {v: k for k, v in ExifTags.TAGS.items()}
    if 'exif' in img.info:
        exif_dict = piexif.load(img.info['exif'])
        dtb = exif_dict['0th'].get(tags['DateTime'], b'0').decode("utf-8")
        if len(dtb) == 1:
            dtb = exif_dict['Exif'].get(tags['DateTimeOriginal'], b'0').decode("utf-8")
        dts = [int(v) for v in regex.split("\:|\s", dtb)]
    else:
        dts = [0]
        exif_dict = {'0th': {}, 'Exif': {}}
    if dts[0] < 1982:
        new_ts = get_timestamp_from_name(f)
        if new_ts is None:
            print(f'Issue with file {f}')
        exif_dict['0th'][tags['DateTime']] = new_ts.strftime('%Y:%m:%d %H:%M').encode("utf-8")
        exif_dict['Exif'][tags['DateTimeOriginal']] = new_ts.strftime('%Y:%m:%d %H:%M').encode("utf-8")
        exif_bytes = piexif.dump(exif_dict)
        img.save(d + "/" + f, "jpeg", exif=exif_bytes)
        print(f'{f}')


if __name__ == '__main__':
    main()
