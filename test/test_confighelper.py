import unittest

from mock import Mock

import cloudwatch.modules.collectd as collectd
from cloudwatch.modules.configuration.confighelper import ConfigHelper
from cloudwatch.modules.configuration.metadatareader import MetadataReader
from helpers.fake_http_server import FakeServer


class ConfigHelperTest(unittest.TestCase):
    CONFIG_DIR = "./test/config_files/"
    VALID_CONFIG_WITH_CREDS_ONLY = CONFIG_DIR + "valid_config_with_creds_only"
    VALID_CONFIG_WITH_CREDS_AND_REGION = CONFIG_DIR + "valid_config_with_creds_and_region"
    VALID_CONFIG_WITH_DEBUG_ENABLED = CONFIG_DIR + "valid_config_with_debug_enabled"
    VALID_CONFIG_WITH_HIGH_RESOLUTION_ONLY = CONFIG_DIR + "valid_config_with_highdefinition"
    VALID_CONFIG_WITHOUT_HIGH_RESOLUTION = CONFIG_DIR + "valid_config_without_highdefinition"
    VALID_CONFIG_FULL = CONFIG_DIR + "valid_config_full"
    VALID_CONFIG_WITH_PASS_THROUGH_ENABLED = CONFIG_DIR + "valid_config_with_pass_through_enabled"
    VALID_CONFIG_WITH_PASS_THROUGH_DISABLED = CONFIG_DIR + "valid_config_with_pass_through_disabled"
    VALID_CONFIG_WITH_PROXY_SERVER_NAME = CONFIG_DIR + "valid_config_with_proxy_server_name"
    VALID_CONFIG_WITH_PROXY_SERVER_PORT = CONFIG_DIR + "valid_config_with_proxy_server_port"
    VALID_CONFIG_WITHOUT_CREDS = CONFIG_DIR + "valid_config_without_creds"
    VALID_CREDENTIALS_FILE = CONFIG_DIR + "valid_credentials_file"
    MISSING_CONFIG = CONFIG_DIR + "no_config"
    PASS_THROUGH_WHITELIST_CONFIG = CONFIG_DIR + "pass_through_whitelist.conf"

    INVALID_CONFIG_WITH_HIGH_RESOLUTION_PARAMETERS = CONFIG_DIR + "invalid_highdefinition_parameters"

    VALID_ACCESS_KEY_STRING = "valid_access_key"
    VALID_SECRET_KEY_STRING = "valid_secret_key"
    VALID_REGION_STRING = "valid_region"
    VALID_HOST_STRING = "valid_host"
    VALID_PROXY_SERVER_NAME = "server_name"
    VALID_PROXY_SERVER_PORT = "server_port"
    VALID_ENABLE_HIGH_DEFINITION_METRICS = "enable_high_definition_metrics"
    VALID_FLUSH_INTERVAL_IN_SECONDS = "flush_interval_in_seconds"

    FAKE_SERVER = None
    
    @classmethod
    def setUpClass(cls):
        cls.FAKE_SERVER = FakeServer()
        cls.FAKE_SERVER.start_server()
        cls.FAKE_SERVER.serve_forever()
        
    def setUp(self):
        self.server = ConfigHelperTest.FAKE_SERVER
        self.server.set_expected_response("", 200)
        self.config_helper = None
        ConfigHelper._DEFAULT_CREDENTIALS_PATH = self.VALID_CREDENTIALS_FILE
    
    def test_get_credentials_from_config_and_region_from_metadata(self):
        self.server.set_expected_response("eu-west-1a", 200)
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_CREDS_ONLY,metadata_server=self.server.get_url())
        assert_credentials(self.config_helper._credentials)
        self.assertEquals(None, self.config_helper.credentials.token)
        self.assertFalse(self.config_helper._use_iam_role_credentials)
        self.assertEquals("eu-west-1", self.config_helper.region)
    
    def test_timeout_on_getting_region_from_metadata(self):
        self.server.set_timeout_delay(MetadataReader._RESPONSE_TIMEOUT_IN_SECONDS * (MetadataReader._TOTAL_RETRIES + 1))
        with self.assertRaises(ValueError):
            self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_CREDS_ONLY,metadata_server=self.server.get_url())
    
    def test_get_full_configuration_from_config_file(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_FULL)
        assert_credentials(self.config_helper.credentials)
        self.assertEquals(None, self.config_helper.credentials.token)
        self.assertFalse(self.config_helper._use_iam_role_credentials)
        self.assertEquals(ConfigHelperTest.VALID_REGION_STRING, self.config_helper.region)
        self.assertTrue(self.config_helper.pass_through)
        self.assertFalse(self.config_helper.debug)
        self.assertEquals(self.VALID_PROXY_SERVER_NAME, self.config_helper.proxy_server_name)
        self.assertEquals(self.VALID_PROXY_SERVER_PORT, self.config_helper.proxy_server_port)
        self.assertEquals(False, self.config_helper.enable_high_definition_metrics)
        self.assertEquals('60', self.config_helper.flush_interval_in_seconds)
    
    def test_debug_is_enabled_by_config_file(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_DEBUG_ENABLED)
        self.assertTrue(self.config_helper.debug)

    def test_with_high_resolution_only_parameters(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_HIGH_RESOLUTION_ONLY)
        self.assertEquals(True, self.config_helper.enable_high_definition_metrics)
        self.assertEquals('60', self.config_helper.flush_interval_in_seconds)

    def test_with_high_resolution_only_default_parameters(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.INVALID_CONFIG_WITH_HIGH_RESOLUTION_PARAMETERS)
        self.assertEquals(False, self.config_helper.enable_high_definition_metrics)
        self.assertEquals('59', self.config_helper.flush_interval_in_seconds)

    def test_with_high_resolution_only(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITHOUT_HIGH_RESOLUTION)
        self.assertEquals(False, self.config_helper.enable_high_definition_metrics)
        self.assertEquals('60', self.config_helper.flush_interval_in_seconds)

    def test_with_proxy_server_name(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_PROXY_SERVER_NAME)
        self.assertEquals(self.VALID_PROXY_SERVER_NAME, self.config_helper.proxy_server_name)

    def test_with_proxy_server_name(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_PROXY_SERVER_PORT)
        self.assertEquals(self.VALID_PROXY_SERVER_PORT, self.config_helper.proxy_server_port)
    
    def test_iam_role_not_refreshed_when_using_credentials_from_file(self):
        self.server.set_expected_response("Error", 404)
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_FULL, metadata_server=self.server.get_url())
        self.config_helper.credentials
        
    def test_configuration_with_missing_credentials(self):
        ConfigHelper._DEFAULT_CREDENTIALS_PATH = ""
        self.server.set_expected_response("", 200)
        with self.assertRaises(ValueError):
            self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITHOUT_CREDS,metadata_server=self.server.get_url())
    
    def test_configuration_with_missing_region(self):
        self.server.set_expected_response('', 200)
        with self.assertRaises(ValueError):
            self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_CREDS_ONLY,metadata_server=self.server.get_url())

    def test_configuration_with_access_key_missing(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_FULL)
        self.config_helper._credentials.access_key = ''
        with self.assertRaises(ValueError):
            self.config_helper._check_configuration_integrity()

    def test_configuration_with_secret_key_missing(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_FULL)
        self.config_helper._credentials.secret_key = ''
        with self.assertRaises(ValueError):
            self.config_helper._check_configuration_integrity()

    def test_set_endpoint_for_localhost(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_FULL)
        self.config_helper.region = "localhost"
        self.config_helper._set_endpoint()
        self.assertEquals("http://localhost/", self.config_helper.endpoint)
    
    def test_set_endpoint_for_valid_region(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_FULL)
        self.config_helper.region = "eu-west-1"
        self.config_helper._set_endpoint()
        self.assertEquals("https://monitoring.eu-west-1.amazonaws.com/", self.config_helper.endpoint)
    
    def test_set_endpoint_from_metadata_server(self):
        self.server.set_expected_response("eu-west-1a", 200)
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_CREDS_ONLY, metadata_server=self.server.get_url())
        self.assertEquals("https://monitoring.eu-west-1.amazonaws.com/", self.config_helper.endpoint)
    
    def test_hostname_loaded_from_file_is_not_overriden_by_metadata(self):
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_FULL, metadata_server=self.server.get_url())
        self.server.set_expected_response("Invalid_hostname", 200)
        self.assertEquals(ConfigHelperTest.VALID_HOST_STRING, self.config_helper.host)

    def test_instance_id_is_used_as_hostname_if_not_specified_in_config(self):
        expected_host = "Valid_Instance_ID"
        self.server.set_expected_response(expected_host, 200)
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_CREDS_ONLY, metadata_server=self.server.get_url())
        self.assertEquals(expected_host, self.config_helper.host)
    
    def test_exception_is_handled_when_instance_id_cannot_be_retrieved(self):
        self.server.set_expected_response("", 404)
        collectd.warning = Mock()
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITH_CREDS_AND_REGION, metadata_server=self.server.get_url())
        self.assertTrue(collectd.warning.called)

    def test_configuration_with_iam_role_credentials(self):
        self._load_and_assert_iam_role_credentials("ACCESS_KEY", "SECRET_KEY", "TOKEN")
    
    def test_iam_role_creds_are_refreshed(self):
        self._load_and_assert_iam_role_credentials("ACCESS_KEY", "SECRET_KEY", "TOKEN")
        creds_json = '{"AccessKeyId" : "NEW_ACCESS_KEY", "SecretAccessKey" : "NEW_SECRET_KEY", "Token" : "NEW_TOKEN" }'
        self._update_and_assert_iam_role_credentials(creds_json, "NEW_ACCESS_KEY", "NEW_SECRET_KEY", "NEW_TOKEN")
        
    def test_old_iam_role_creds_are_served_on_error(self):
        self._load_and_assert_iam_role_credentials("ACCESS_KEY", "SECRET_KEY", "TOKEN")
        creds_json = '{"AccessKeyId" : "NEW_ACCESS_KEY", "SecretAccessKey" : "NEW_SECRET_KEY",}'
        self._update_and_assert_iam_role_credentials(creds_json, "ACCESS_KEY", "SECRET_KEY", "TOKEN")

    def test_whitelist_is_properly_configured_based_on_plugin_config_file(self):
        ConfigHelper.WHITELIST_CONFIG_PATH = self.PASS_THROUGH_WHITELIST_CONFIG
        self.config_helper = ConfigHelper(config_path=self.VALID_CONFIG_WITH_PASS_THROUGH_DISABLED)
        self.assertFalse(self.config_helper.whitelist.is_whitelisted("random-metric-name"))
        self.config_helper = ConfigHelper(config_path=self.VALID_CONFIG_WITH_PASS_THROUGH_ENABLED)
        self.assertTrue(self.config_helper.whitelist.is_whitelisted("random-metric-name"))
        
    def _load_and_assert_iam_role_credentials(self, expected_access, expected_secret, expected_token):
        creds_json = '{"AccessKeyId" : "' + expected_access +'", "SecretAccessKey" : "' + expected_secret + '", "Token" : "' + expected_token + '" }'
        self.server.set_expected_response(creds_json, 200)
        ConfigHelper._DEFAULT_CREDENTIALS_PATH = ""
        self.config_helper = ConfigHelper(config_path=ConfigHelperTest.VALID_CONFIG_WITHOUT_CREDS,metadata_server=self.server.get_url())
        assert_credentials(self.config_helper._credentials, expected_access, expected_secret, expected_token)

    def _update_and_assert_iam_role_credentials(self, json, expected_access, expected_secret, expected_token):
        self.server.set_expected_response(json, 200)
        creds = self.config_helper.credentials
        assert_credentials(creds, expected_access, expected_secret, expected_token)
        
    @classmethod
    def tearDownClass(cls):
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None


def assert_credentials(credentials, expected_access=ConfigHelperTest.VALID_ACCESS_KEY_STRING, 
                       expected_secret=ConfigHelperTest.VALID_SECRET_KEY_STRING, expected_token=None):
    assert credentials.access_key == expected_access
    assert credentials.secret_key == expected_secret
    assert credentials.token == expected_token

