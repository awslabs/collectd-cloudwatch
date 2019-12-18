import unittest
import requests
from helpers.fake_http_server import FakeServer
from helpers.fake_metadata import FAKE_REGION, FAKE_IDENTITY_DOCUMENT_STRING
from cloudwatch.modules.configuration.metadatareader import MetadataReader, MetadataRequestException

class MetadataReaderTest(unittest.TestCase):
    FAKE_SERVER = None
    MINIMUM_NUMBER_OF_RETRIES = 3
    MAXIMUM_NUMBER_OF_RETRIES = 5
    
    @classmethod
    def setUpClass(cls):
        cls.FAKE_SERVER = FakeServer()
        cls.FAKE_SERVER.start_server()
        cls.FAKE_SERVER.serve_forever()
        
    def setUp(self):
        self.server = MetadataReaderTest.FAKE_SERVER
        self.server.set_expected_response(FAKE_IDENTITY_DOCUMENT_STRING, 200)
        self.metadata_reader = MetadataReader(self.server.get_url())
    
    def test_number_of_retries_is_within_expected_range(self):
        retries = MetadataReader._TOTAL_RETRIES
        if retries < self.MINIMUM_NUMBER_OF_RETRIES or retries > self.MAXIMUM_NUMBER_OF_RETRIES:
            self.fail("The total number of retries for metadata reader is invalid")
    
    def test_get_region_from_metadata(self):
        self.server.set_expected_response(FAKE_IDENTITY_DOCUMENT_STRING, 200)
        self.assertEquals(FAKE_REGION, self.metadata_reader.get_region())
    
    def test_get_full_configuration_from_config_file(self):
        self.server.set_expected_response("invalid request", 404)
        with self.assertRaises(MetadataRequestException):
            self.metadata_reader._get_metadata("invalid_request")
            
    def test_request_timeout(self):
        self.server.set_timeout_delay(MetadataReader._RESPONSE_TIMEOUT_IN_SECONDS * (MetadataReader._TOTAL_RETRIES + 1))
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.metadata_reader.get_region()
            
    def test_retry_is_working_on_timeouts(self):
        self.server.set_timeout_delay(MetadataReader._RESPONSE_TIMEOUT_IN_SECONDS * (MetadataReader._TOTAL_RETRIES - 1))
        self.metadata_reader.get_region()
        
    def test_request_timeout_on_invalid_host(self):
        self.metadata_reader.metadata_server = "http://invalid_server/"
        with self.assertRaises(requests.exceptions.ConnectionError):
            self.metadata_reader.get_region()
    
    def test_can_get_iam_role_name(self):
        self.server.set_expected_response("collectd-test", 200)
        self.assertEquals("collectd-test", self.metadata_reader.get_iam_role_name())
    
    def test_can_create_iam_role_credentials_from_json(self):
        json = '{"Code" : "Success", "LastUpdated" : "2015-08-27T09:22:57Z", "Type" : "AWS-HMAC", \
          "AccessKeyId" : "ACCESS_KEY", "SecretAccessKey" : "SECRET_KEY", "Token" : "TOKEN", \
          "Expiration" : "2015-08-27T09:22:57Z" }'
        self.server.set_expected_response(json, 200)
        creds = self.metadata_reader.get_iam_role_credentials("Collectd-Test")
        self.assertEquals("ACCESS_KEY", creds.access_key)
        self.assertEquals("SECRET_KEY", creds.secret_key)
        self.assertEquals("TOKEN", creds.token)
    
    def test_get_iam_role_credentials_raises_exception_on_invalid_json_format(self):
        json = '{"Code" - "Success", "LastUpdated" : "2015-08-27T09:22:57Z", "Type" : "AWS-HMAC", \
          "AccessKeyId" : "ACCESS_KEY", "SecretAccessKey" : "SECRET_KEY", "Token" : "TOKEN", \
          "Expiration" : "2015-08-27T09:22:57Z" }'
        self.server.set_expected_response(json, 200)
        with self.assertRaises(ValueError):
            self.metadata_reader.get_iam_role_credentials("Collectd-Test")
    
    def test_get_iam_role_credentials_raises_exception_on_missing_values(self):
        json = '{"AccessKeyId" : "ACCESS_KEY", "SecretAccessKey" : "SECRET_KEY", "Token" : "" }'
        self.server.set_expected_response(json, 200)
        with self.assertRaises(ValueError):
            self.metadata_reader.get_iam_role_credentials("Collectd-Test")
    
    @classmethod
    def tearDownClass(cls):    
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None
