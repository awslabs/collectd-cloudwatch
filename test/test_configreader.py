import unittest

from mock import MagicMock, Mock

from cloudwatch.modules.configuration.configreader import ConfigReader


class ConfigReaderTest(unittest.TestCase):
    CONFIG_DIR = "./test/config_files/"
    VALID_CONFIG_WITH_CREDS_ONLY = CONFIG_DIR + "valid_config_with_creds_only"
    VALID_CONFIG_FULL = CONFIG_DIR + "valid_config_full"
    VALID_CONFIG_WITHOUT_CREDS = CONFIG_DIR + "valid_config_without_creds"
    VALID_CONFIG_WITH_WHITE_SPACES = CONFIG_DIR + "valid_config_with_white_spaces"
    VALID_CONFIG_WITH_DEBUG_ENABLED = CONFIG_DIR + "valid_config_with_debug_enabled"
    VALID_CONFIG_WITH_DEBUG_DISABLED = CONFIG_DIR + "valid_config_with_debug_disabled"
    VALID_CONFIG_WITH_PROXY_SERVER_NAME = CONFIG_DIR + "valid_config_with_proxy_server_name"
    VALID_CONFIG_WITH_PROXY_SERVER_PORT = CONFIG_DIR + "valid_config_with_proxy_server_port"
    VALID_CONFIG_WITH_PASS_THROUGH_ENABLED = CONFIG_DIR + "valid_config_with_pass_through_enabled"
    VALID_CONFIG_WITH_PASS_THROUGH_DISABLED = CONFIG_DIR + "valid_config_with_pass_through_disabled"
    INVALID_CONFIG_WITH_UNKNOWN_PARAMETER = CONFIG_DIR + "invalid_config_with_unknown_parameters"
    INVALID_CONFIG_WITH_SYNTAX_ERROR = CONFIG_DIR + "invalid_config_with_syntax_error"
    INVALID_CONFIG_WITH_SINGLE_KEY_MISSING = CONFIG_DIR + "invalid_config_full_with_single_key_missing"
    MISSING_CONFIG = CONFIG_DIR + "no_config"
    VALID_ACCESS_KEY_STRING = "valid_access_key"
    VALID_SECRET_KEY_STRING = "valid_secret_key"
    VALID_REGION_STRING = "valid_region"
    VALID_HOST_STRING = "valid_host"
    VALID_PUSH_ASG_AND_CONSTANT = CONFIG_DIR + "valid_config_push_constant_and_asg"
    VALID_PROXY_SERVER_NAME = "server_name"
    VALID_PROXY_SERVER_PORT = "server_port"
    
    def setUp(self):
        self.config_reader = None
        self.logger = MagicMock()
        self.logger.warning = Mock()
        ConfigReader._LOGGER = self.logger

    def test_get_credentials_path_from_config(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_FULL)
        self.assertEquals("./test/config_files/valid_credentials_file", self.config_reader.credentials_path)

    def test_push_asg_false(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_FULL)
        self.assertFalse(self.config_reader.push_asg)

    def test_push_constant_false(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_FULL)
        self.assertFalse(self.config_reader.push_constant)

    def test_push_constant_true(self):
        self.config_reader = ConfigReader(self.VALID_PUSH_ASG_AND_CONSTANT)
        self.assertTrue(self.config_reader.push_constant)
        self.assertEquals("potato", self.config_reader.constant_dimension_value)
    
    def test_push_asg_true(self):
        self.config_reader = ConfigReader(self.VALID_PUSH_ASG_AND_CONSTANT)
        self.assertTrue(self.config_reader.push_asg)
        
    def test_get_full_configuration(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_FULL)
        self.assertEquals(self.VALID_REGION_STRING, self.config_reader.region)
        self.assertEquals(self.VALID_HOST_STRING, self.config_reader.host)
        self.assertFalse(self.config_reader.debug)
        self.assertEquals(self.VALID_PROXY_SERVER_NAME, self.config_reader.proxy_server_name)
        self.assertEquals(self.VALID_PROXY_SERVER_PORT, self.config_reader.proxy_server_port)
    
    def test_valid_config_with_debug_enabled(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITH_DEBUG_ENABLED)
        self.assertTrue(self.config_reader.debug)

    def test_valid_config_with_debug_disabled(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITH_DEBUG_DISABLED)
        self.assertFalse(self.config_reader.debug)

    def test_valid_config_with_proxy_server_name(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITH_PROXY_SERVER_NAME)
        self.assertEquals(self.VALID_PROXY_SERVER_NAME, self.config_reader.proxy_server_name)

    def test_valid_config_with_proxy_server_port(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITH_PROXY_SERVER_PORT)
        self.assertEquals(self.VALID_PROXY_SERVER_PORT, self.config_reader.proxy_server_port)

    def test_valid_config_with_pass_through_enabled(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITH_PASS_THROUGH_ENABLED)
        self.assertTrue(self.config_reader.pass_through)

    def test_valid_config_with_pass_through_disabled(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITH_PASS_THROUGH_DISABLED)
        self.assertFalse(self.config_reader.pass_through)

    def test_default_configurations(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITHOUT_CREDS)
        self.assertFalse(self.config_reader.pass_through)
        self.assertFalse(self.config_reader.debug)

    def test_get_configuration_without_credentials(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITHOUT_CREDS)
        self.assertFalse(self.config_reader.credentials_path)
        self.assertEquals(self.VALID_REGION_STRING, self.config_reader.region)
        self.assertEquals(self.VALID_HOST_STRING, self.config_reader.host)
        
    def test_strip_whitespaces_from_config_file(self):
        self.config_reader = ConfigReader(self.VALID_CONFIG_WITH_WHITE_SPACES)
        self.assertEquals(self.VALID_REGION_STRING, self.config_reader.region)
        self.assertEquals(self.VALID_HOST_STRING, self.config_reader.host)
    
    def test_config_file_is_missing(self):
        logger = MagicMock()
        logger.warning = Mock()
        ConfigReader._LOGGER = logger
        with self.assertRaises(Exception):
            self.config_reader = ConfigReader(self.MISSING_CONFIG)
            self.assertTrue(logger.warning.called)
    
    def test_config_reader_without_path(self):
        with self.assertRaises(TypeError):
            self.config_reader = ConfigReader()
