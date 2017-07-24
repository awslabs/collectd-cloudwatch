import unittest

from mock import MagicMock, Mock

from cloudwatch.modules.configuration.readerutils import ReaderUtils

class ReaderUtilsTest(unittest.TestCase):
    CONFIG_DIR = "./test/config_files/"
    VALID_CONFIG_FULL = CONFIG_DIR + "valid_config_full"
    VALID_CONFIG_FULL_QUOTED = CONFIG_DIR + "valid_config_full_quoted"
    VALID_REAL_CONFIG = CONFIG_DIR + "valid_real_plugin_conf"
    VALID_CONFIG_WITH_WHITE_SPACES = CONFIG_DIR + "valid_config_with_white_spaces"
    VALID_CONFIG_WITH_COMMENTS = CONFIG_DIR + "valid_config_with_comments"
    VALID_CONFIG_WITH_DEBUG_ENABLED = CONFIG_DIR + "valid_config_with_debug_enabled"
    VALID_CONFIG_WITH_DEBUG_DISABLED = CONFIG_DIR + "valid_config_with_debug_disabled"
    INVALID_CONFIG_WITH_DEBUG = CONFIG_DIR + "invalid_config_with_debug"
    INVALID_CONFIG_WITH_SYNTAX_ERROR = CONFIG_DIR + "invalid_config_with_syntax_error"
    INVALID_CONFIG_WITH_HIGH_RESOLUTION_PARAMETERS = CONFIG_DIR + "invalid_highdefinition_parameters"
    MISSING_CONFIG = CONFIG_DIR + "no_config"
    VALID_ACCESS_KEY_STRING = "valid_access_key"
    VALID_SECRET_KEY_STRING = "valid_secret_key"
    VALID_REGION_STRING = "valid_region"
    VALID_HOST_STRING = "valid_host"
    VALID_CREDENTIALS_PATH_STRING = "./test/config_files/valid_credentials_file"
    
    def setUp(self):
        self.logger = MagicMock()
        self.logger.error = Mock()
        ReaderUtils._LOGGER = self.logger

    def test_get_string_without_quotes(self):
        reader = ReaderUtils(self.VALID_CONFIG_FULL)
        region = reader.get_string("region")
        credentials_path = reader.get_string("credentials_path")
        host = reader.get_string("host")
        self.assertEquals(self.VALID_REGION_STRING, region)
        self.assertEquals(self.VALID_HOST_STRING, host)
        self.assertEquals(self.VALID_CREDENTIALS_PATH_STRING, credentials_path)
        
    def test_get_string_with_quotes(self):
        reader = ReaderUtils(self.VALID_CONFIG_FULL_QUOTED)
        region = reader.get_string("region")
        credentials_path = reader.get_string("credentials_path")
        host = reader.get_string("host")
        self.assertEquals(self.VALID_REGION_STRING, region)
        self.assertEquals(self.VALID_HOST_STRING, host)
        self.assertEquals(self.VALID_CREDENTIALS_PATH_STRING, credentials_path)
        
    def test_get_boolean(self):
        reader = ReaderUtils(self.VALID_CONFIG_WITH_DEBUG_DISABLED)
        self.assertEquals(False, reader.get_boolean("debug"))
        reader = ReaderUtils(self.VALID_CONFIG_WITH_DEBUG_ENABLED)
        self.assertEquals(True, reader.get_boolean("debug"))

    def test_try_get_boolean_does_not_raise_on_error(self):
        reader = ReaderUtils(self.VALID_CONFIG_WITH_DEBUG_ENABLED)
        reader.try_get_boolean('invalid', True)

    def test_try_get_boolean_returns_default_on_error(self):
        reader = ReaderUtils(self.VALID_CONFIG_WITH_DEBUG_ENABLED)
        self.assertTrue(reader.try_get_boolean('invalid', True))

    def test_try_get_boolean_returns_actual_value_when_possible(self):
        reader = ReaderUtils(self.VALID_CONFIG_WITH_DEBUG_DISABLED)
        self.assertFalse(reader.try_get_boolean('debug', True))

    def test_try_get_high_resolution_parameters(self):
        reader = ReaderUtils(self.INVALID_CONFIG_WITH_HIGH_RESOLUTION_PARAMETERS)
        enable_high_definition_metrics = reader.get_string("enable_high_definition_metrics")
        flush_interval_in_seconds = reader.get_string("flush_interval_in_seconds")
        self.assertEquals('Tru', enable_high_definition_metrics);
        self.assertEquals('59', flush_interval_in_seconds);

    def test_get_boolean_from_invalid_config(self):
        reader = ReaderUtils(self.INVALID_CONFIG_WITH_DEBUG)
        with self.assertRaises(ValueError):
            reader.get_boolean("debug")
    
    def test_whitespaces_are_stripped_correctly(self):
        reader = ReaderUtils(self.VALID_CONFIG_WITH_WHITE_SPACES)
        region = reader.get_string("region")
        host = reader.get_string("host")
        self.assertEquals(self.VALID_REGION_STRING, region)
        self.assertEquals(self.VALID_HOST_STRING, host)
        
    def test_configuration_with_comments(self):
        reader = ReaderUtils(self.VALID_CONFIG_WITH_COMMENTS)
        region = reader.get_string("region")
        host = reader.get_string("host")
        self.assertEquals(self.VALID_REGION_STRING, region)
        self.assertEquals(self.VALID_HOST_STRING, host)
        
    def test_strip_quotes(self):
        reader = ReaderUtils(self.VALID_CONFIG_FULL)
        result = reader._strip_quotes("'string'")
        self.assertEquals("string", result)
        result = reader._strip_quotes('"string2"')
        self.assertEquals("string2", result)
        result = reader._strip_quotes('"s"tring"3"')
        self.assertEquals("s\"tring\"3", result)
        result = reader._strip_quotes("'s'tring'4'")
        self.assertEquals("s'tring'4", result)
        result = reader._strip_quotes("''string5''")
        self.assertEquals("'string5'", result)
        result = reader._strip_quotes("'\"string6\"'")
        self.assertEquals("\"string6\"", result)
        result = reader._strip_quotes("'string7")
        self.assertEquals("string7", result)
        result = reader._strip_quotes("string8\"")
        self.assertEquals("string8", result)
    
    def test_valid_real_config(self):
        reader = ReaderUtils(self.VALID_REAL_CONFIG)
        region = reader.get_string("region")
        self.assertEquals("", region) # region is commented out
        host = reader.get_string("host")
        self.assertEquals("Server1", host)
        credentials_path = reader.get_string("credentials_path")
        self.assertEquals("/home/user/.aws/credentials", credentials_path)
        debug = reader.get_boolean("debug")
        self.assertEquals(False, debug)
        
    def test_parse_missing_config(self):
        with self.assertRaises(IOError):
            ReaderUtils(self.MISSING_CONFIG)
    
    def test_parse_config_with_invalid_syntax(self):
        reader = ReaderUtils(self.INVALID_CONFIG_WITH_SYNTAX_ERROR)
        with self.assertRaises(ValueError):
            reader.get_string("region")
        self.assertTrue(self.logger.error.called)
