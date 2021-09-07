from unittest import TestCase

from media_process import get_timestamp, process_file


class Test(TestCase):
    def test_process_file(self):
        path_name, file_name = get_timestamp('samples/d1/20140822132330_DSC_0016.JPG')
        self.assertEqual('20140822132330', file_name)
        self.assertEqual('2014/08', path_name)

    def test_process_file2(self):
        path_name, file_name = get_timestamp('samples/d1/d2/Фото0007.jpeg')
        self.assertEqual('20130106144641', file_name)
        self.assertEqual('2013/01', path_name)

    def test_process_file3(self):
        path_name, file_name = get_timestamp('samples/f2269376.jpg')
        self.assertEqual('20190325161019', file_name)
        self.assertEqual('2019/03', path_name)

    def test_scan_files(self):
        file_changes = process_file('samples/')
        self.assertEqual(4, len(file_changes))
