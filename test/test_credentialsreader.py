import unittest

from mock import MagicMock, Mock
from cloudwatch.modules.configuration.credentialsreader import CredentialsReader, CredentialsReaderException

class CredentialsReaderTest(unittest.TestCase):
    CONFIG_DIR = "./test/config_files/"
    VALID_CREDENTIALS_FILE = CONFIG_DIR + "valid_credentials_file"
    VALID_CREDENTIALS_FILE_AWS_FORMAT = CONFIG_DIR + "valid_credentials_file_aws_format"
    VALID_CREDENTIALS_FILE_AWS_FORMAT_MIXED = CONFIG_DIR + "valid_credentials_file_aws_format_mixed"
    VALID_CREDENTIALS_FILE_AWS_FORMAT_PROFILE_PRESENT = CONFIG_DIR + "valid_credentials_file_aws_format_profile_present"
    VALID_CREDENTIALS_FILE_WITH_WHITESPACES = CONFIG_DIR + "valid_credentials_file_with_whitespaces"
    INVALID_CREDENTIALS_FILE_WITH_UNKNOWN_PARAMETER = CONFIG_DIR + "invalid_credentials_file_with_unknown_parameters"
    INVALID_CREDENTIALS_FILE_WITH_SYNTAX_ERROR = CONFIG_DIR + "invalid_credentials_file_with_syntax_error"
    INVALID_CREDENTIALS_FILE_WITH_ACCESS_KEY_MISSING = CONFIG_DIR + "invalid_credentials_file_with_access_key_missing"
    INVALID_CREDENTIALS_FILE_WITH_SECRET_KEY_MISSING = CONFIG_DIR + "invalid_credentials_file_with_secret_key_missing"
    MISSING_CONFIG = CONFIG_DIR + "no_config"
    VALID_ACCESS_KEY_STRING = "valid_access_key"
    VALID_SECRET_KEY_STRING = "valid_secret_key"
    
    def setUp(self):
        self.credentials_reader = None    
        self.logger = MagicMock()
        self.logger.warning = Mock()
        CredentialsReader._LOGGER = self.logger

    def test_get_credentials_from_file(self):
        self.credentials_reader = CredentialsReader(self.VALID_CREDENTIALS_FILE)
        assert_credentials(self.credentials_reader)
        
    def test_strip_whitespaces_from_credentials_file(self):
        self.credentials_reader = CredentialsReader(self.VALID_CREDENTIALS_FILE_WITH_WHITESPACES)
        assert_credentials(self.credentials_reader)

    def test_get_credentials_aws_format(self):
        self.credentials_reader = CredentialsReader(self.VALID_CREDENTIALS_FILE_AWS_FORMAT)
        assert_credentials(self.credentials_reader)

    def test_get_credentials_aws_format_mixed(self):
        self.credentials_reader = CredentialsReader(self.VALID_CREDENTIALS_FILE_AWS_FORMAT_MIXED)
        assert_credentials(self.credentials_reader)

    def test_get_credentials_aws_format_profile_present(self):
        self.credentials_reader = CredentialsReader(self.VALID_CREDENTIALS_FILE_AWS_FORMAT_PROFILE_PRESENT)
        assert_credentials(self.credentials_reader)
    
    def test_credentials_file_with_single_key_missing(self):
        with self.assertRaises(CredentialsReaderException):
            self.credentials_reader = CredentialsReader(self.INVALID_CREDENTIALS_FILE_WITH_ACCESS_KEY_MISSING)
            self.assertTrue(self.logger.warning.called)
        with self.assertRaises(CredentialsReaderException):
            self.credentials_reader = CredentialsReader(self.INVALID_CREDENTIALS_FILE_WITH_SECRET_KEY_MISSING)
            self.assertTrue(self.logger.warning.called)

    def test_config_file_is_missing(self):
        logger = MagicMock()
        logger.warning = Mock()
        CredentialsReader._LOGGER = logger
        self.credentials_reader = CredentialsReader(self.MISSING_CONFIG)
        self.assertTrue(logger.warning.called)
    
    def test_config_reader_without_path(self):
        with self.assertRaises(TypeError):
            self.config_reader = CredentialsReader()

def assert_credentials(credentials_reader):
    assert credentials_reader.credentials
    creds = credentials_reader.credentials
    assert creds.access_key == CredentialsReaderTest.VALID_ACCESS_KEY_STRING
    assert creds.secret_key == CredentialsReaderTest.VALID_SECRET_KEY_STRING
    
