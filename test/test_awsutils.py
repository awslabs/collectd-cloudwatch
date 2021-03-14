import re
import unittest

from cloudwatch.modules.awsutils import get_aws_timestamp, get_datestamp


class AWSUtilsTest(unittest.TestCase):
    
    def test_get_timestamp_format(self):
        pattern = re.compile(r'\d\d\d\d\d\d\d\dT\d\d\d\d\d\dZ')
        self.assertTrue(pattern.match(get_aws_timestamp()), "Expected timestamp in the format YYYYMMDDThhmmssZ.")
                    
    def test_get_datestamp_format(self):
        pattern = re.compile(r'\d\d\d\d\d\d\d\d')
        self.assertTrue(pattern.match(get_datestamp()))
