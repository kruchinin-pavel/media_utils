from unittest import TestCase

from media_process import get_timestamp


class Test(TestCase):
    def test_process_file(self):
        path_name, file_name = get_timestamp('samples/20140822132330_DSC_0016.JPG')
        self.assertEqual('20140822132330', file_name)
        self.assertEqual('2014/08', path_name)

    def test_process_file2(self):
        path_name, file_name = get_timestamp('samples/Фото0007.jpg')
        self.assertEqual('20130106144641', file_name)
        self.assertEqual('2013/01', path_name)
