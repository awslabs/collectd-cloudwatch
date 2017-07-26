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
        self.config_helper.enable_high_resolution_metrics = False
        self.server = self.FAKE_SERVER
        self.server.set_expected_response("OK", 200)
    
    def test_build_no_add(self):
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal")
        self.config_helper.push_asg = False
        self.config_helper.push_constant = False
        metric = MetricDataBuilder(self.config_helper, vl).build()
        self.assertEquals(None, metric[0].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[0].metric_name)
        self.assertEquals("valid_host", metric[0].dimensions['Host'])
        self.assertEquals("0", metric[0].dimensions['PluginInstance'])
        self.assertEquals(1, len(metric))

    def test_build_add_asg(self):
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal")
        self.config_helper.push_asg = True
        self.config_helper.push_constant = False
        self.config_helper.asg_name = "MyASG"
        metric = MetricDataBuilder(self.config_helper, vl).build()
        self.assertEquals(None, metric[0].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[0].metric_name)
        self.assertEquals("valid_host", metric[0].dimensions['Host'])
        self.assertEquals("0", metric[0].dimensions['PluginInstance'])
        self.assertEquals(2, len(metric))
        self.assertEquals(None, metric[1].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[1].metric_name)
        self.assertEquals("MyASG", metric[1].dimensions['AutoScalingGroup'])
        self.assertEquals("0", metric[1].dimensions['PluginInstance'])

    def test_build_add_constant(self):
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal")
        self.config_helper.push_asg = False
        self.config_helper.push_constant = True
        self.config_helper.constant_dimension_value = "somevalue"
        metric = MetricDataBuilder(self.config_helper, vl).build()
        self.assertEquals(None, metric[0].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[0].metric_name)
        self.assertEquals("valid_host", metric[0].dimensions['Host'])
        self.assertEquals("0", metric[0].dimensions['PluginInstance'])
        self.assertEquals(2, len(metric))
        self.assertEquals(None, metric[1].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[1].metric_name)
        self.assertEquals("somevalue", metric[1].dimensions['FixedDimension'])
        self.assertEquals("0", metric[1].dimensions['PluginInstance'])

    def test_build_add_constant_and_asg(self):
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal")
        self.config_helper.push_asg = True
        self.config_helper.asg_name = "MyASG"
        self.config_helper.push_constant = True
        self.config_helper.constant_dimension_value = "somevalue"
        metric = MetricDataBuilder(self.config_helper, vl).build()
        self.assertEquals(None, metric[0].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[0].metric_name)
        self.assertEquals("valid_host", metric[0].dimensions['Host'])
        self.assertEquals("0", metric[0].dimensions['PluginInstance'])
        self.assertEquals(3, len(metric))
        self.assertEquals(None, metric[1].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[1].metric_name)
        self.assertEquals("MyASG", metric[1].dimensions['AutoScalingGroup'])
        self.assertEquals("0", metric[1].dimensions['PluginInstance'])
        self.assertEquals(None, metric[2].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[2].metric_name)
        self.assertEquals("somevalue", metric[2].dimensions['FixedDimension'])
        self.assertEquals("0", metric[2].dimensions['PluginInstance'])

    def test_build_with_enable_high_resolution_metrics(self):
        self.config_helper = MagicMock()
        self.config_helper.push_asg = False
        self.config_helper.push_constant = False
        self.config_helper.endpoint = "valid_endpoint"
        self.config_helper.host = "valid_host"
        self.config_helper.region = "localhost"
        self.config_helper.enable_high_resolution_metrics = True
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal", 112.1)
        metric = MetricDataBuilder(self.config_helper, vl, 160.1).build()
        self.assertEquals(None, metric[0].statistics)
        self.assertEquals("CPU.CPU.Steal", metric[0].metric_name)
        self.assertEquals("valid_host", metric[0].dimensions['Host'])
        self.assertEquals("0", metric[0].dimensions['PluginInstance'])
        self.assertEquals("19700101T000240Z", metric[0].timestamp);
    
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
        
    def _get_vl_mock(self, plugin, plugin_instance, type, type_instance, host="MockHost", values=[], timestamp=0):
        vl = MagicMock()
        vl.plugin = plugin
        vl.plugin_instance = plugin_instance
        vl.type = type
        vl.type_instance = type_instance
        vl.host = host
        vl.values = values
        vl.time = timestamp
        return vl
        
    @classmethod
    def tearDownClass(cls):    
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None