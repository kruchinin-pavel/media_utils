from unittest import TestCase

from media_process import get_timestamp


class Test(TestCase):
    def test_process_file(self):
        path_name, file_name = get_timestamp('samples/20140822132330_DSC_0016.JPG')
        self.assertEqual('20140822132330', file_name)
        self.assertEqual('2014/08', path_name)
