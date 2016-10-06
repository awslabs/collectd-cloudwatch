import unittest

from mock import MagicMock
from helpers.fake_http_server import FakeServer
from cloudwatch.modules.configuration.confighelper import ConfigHelper
from cloudwatch.modules.metricdata import MetricDataBuilder

class MetricDataBuilderTest(unittest.TestCase):

    FAKE_SERVER = None
    CONFIG_DIR = "./test/config_files/"
    VALID_CONFIG_FULL = CONFIG_DIR + "valid_config_full"
    VALID_CONFIG_WITH_CREDS_AND_REGION = CONFIG_DIR + "valid_config_with_creds_and_region"
    
    @classmethod
    def setUpClass(cls):
        cls.FAKE_SERVER = FakeServer()
        cls.FAKE_SERVER.start_server()
        cls.FAKE_SERVER.serve_forever()
        
    def setUp(self):
        self.config_helper = MagicMock()
        self.config_helper.endpoint = "valid_endpoint"
        self.config_helper.host = "valid_host"
        self.config_helper.region = "localhost"
        self.server = self.FAKE_SERVER
        self.server.set_expected_response("OK", 200)
    
    def test_build(self):
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal")
        metric = MetricDataBuilder(self.config_helper, vl).build()
        self.assertEquals(None, metric.statistics)
        self.assertEquals("CPU.CPU.Steal", metric.metric_name)
        self.assertEquals("valid_host", metric.dimensions['Host'])
        self.assertEquals("0", metric.dimensions['PluginInstance'])
    
    def test_build_metric_name_with_all_name_parts(self):
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal")
        metric_data_builder = MetricDataBuilder(self.config_helper, vl)
        expected_name = vl.plugin + "." + vl.type + "." + vl.type_instance
        generated_name = metric_data_builder._build_metric_name()
        self.assertEquals(expected_name, generated_name)

    def test_build_metric_name_with_required_name_parts_only(self):
        vl = self._get_vl_mock("CPU", "", "CPU", "")
        metric_data_builder = MetricDataBuilder(self.config_helper, vl)
        expected_name = vl.plugin + "." + vl.type
        generated_name = metric_data_builder._build_metric_name()
        self.assertEquals(expected_name, generated_name)

    def test_build_metric_name_with_real_CPU_name_parts_only(self):
        vl = self._get_vl_mock("CPU", "", "CPU", "Steal")
        metric_data_builder = MetricDataBuilder(self.config_helper, vl)
        expected_name = vl.plugin + "." + vl.type + "." + vl.type_instance
        generated_name = metric_data_builder._build_metric_name()
        self.assertEquals(expected_name, generated_name)
    
    def test_build_metric_dimensions(self):
        vl = self._get_vl_mock("aggregation", "cpu-average", "cpu", "idle")
        metric_data_builder = MetricDataBuilder(self.config_helper, vl)
        dimensions = metric_data_builder._build_metric_dimensions()
        self.assertEquals("cpu-average", dimensions['PluginInstance'])
        self.assertEquals("valid_host", dimensions['Host'])

    def test_buoild_metric_dimensions_with_no_plugin_instance(self):
        vl = self._get_vl_mock("plugin", "", "type", "")
        metric_data_builder = MetricDataBuilder(self.config_helper, vl)
        dimensions = metric_data_builder._build_metric_dimensions()
        self.assertEquals("NONE", dimensions['PluginInstance'])    

    def test_build_metric_dimensions_with_host_from_value_list(self):
        self.server.set_expected_response("Error", 404)
        self.config_helper.host = ""
        vl = self._get_vl_mock("aggregation", "cpu-average", "cpu", "idle")
        metric_data_builder = MetricDataBuilder(self.config_helper, vl)
        dimensions = metric_data_builder._build_metric_dimensions()
        self.assertEquals("MockHost", dimensions['Host'])
        
    def _get_vl_mock(self, plugin, plugin_instance, type, type_instance, host="MockHost", values=[]):
        vl = MagicMock()
        vl.plugin = plugin
        vl.plugin_instance = plugin_instance
        vl.type = type
        vl.type_instance = type_instance
        vl.host = host
        vl.values = values
        return vl
        
    @classmethod
    def tearDownClass(cls):    
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None