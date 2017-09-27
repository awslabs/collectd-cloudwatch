import unittest
import os

from time import time, sleep

from cloudwatch.modules.collectd_integration.dataset import CollectdDatasetResolver
from helpers.fake_http_server import FakeServer
from mock import patch, MagicMock, Mock
from cloudwatch.modules.configuration.confighelper import ConfigHelper
from cloudwatch.modules.flusher import Flusher
from cloudwatch.modules.metricdata import MetricDataBuilder
from cloudwatch.modules.configuration.whitelist import Whitelist


_DS_data = {
    'multivalue_type': ['name1', 'name2'],
    'CPU': ['value']
}


def _get_mocked_ds(ds_type):
    if ds_type in _DS_data:
        return _DS_data[ds_type]

    else:
        raise ValueError(ds_type)


class FlusherTest(unittest.TestCase):

    FAKE_SERVER = None
    CONFIG_DIR = "./test/config_files/"
    VALID_CONFIG_FULL = CONFIG_DIR + "valid_config_full"
    VALID_CONFIG_WITH_CREDS_AND_REGION = CONFIG_DIR + "valid_config_with_creds_and_region"
    VALID_CONFIG_WITH_DRYRUN_ENABLED = CONFIG_DIR + "valid_config_with_dryrun_enabled"
    VALID_CONFIG_WITHOUT_ENABLE_HIGH_DEFINITION_METRICS = CONFIG_DIR + "valid_config_without_highdefinition"

    @classmethod
    def setUpClass(cls):
        cls.FAKE_SERVER = FakeServer()
        cls.FAKE_SERVER.start_server()
        cls.FAKE_SERVER.serve_forever()

    def setUp(self):
        self.server = self.FAKE_SERVER
        self.server.set_expected_response("OK", 200)
        self.config_helper = ConfigHelper(config_path=self.VALID_CONFIG_FULL)
        self.config_helper.endpoint = self.server.get_url()
        self.config_helper.enable_high_resolution_metrics = False
        self.config_helper.whitelist = Mock(spec=Whitelist)
        self.dataset_resolver = Mock(spec=CollectdDatasetResolver)
        self.dataset_resolver.get_dataset_names = Mock(side_effect=_get_mocked_ds)
        self.flusher = Flusher(config_helper=self.config_helper, dataset_resolver=self.dataset_resolver)
        self.client = MagicMock()
        self.client.put_metric_data = Mock()
        self.flusher.client = self.client

    def test_is_numerical_value(self):
        self.assertFalse(self.flusher.is_numerical_value(float('nan')))
        self.assertTrue(self.flusher.is_numerical_value(2))
        self.assertTrue(self.flusher.is_numerical_value(2.01))
        self.assertTrue(self.flusher.is_numerical_value("+1.2"))
        self.assertTrue(self.flusher.is_numerical_value("-1.2"))
        self.assertTrue(self.flusher.is_numerical_value("1.2"))
        self.assertTrue(self.flusher.is_numerical_value("1"))
        self.assertTrue(self.flusher.is_numerical_value("0.211"))
        self.assertTrue(self.flusher.is_numerical_value(".211"))
        self.assertFalse(self.flusher.is_numerical_value("@.211"))
        self.assertFalse(self.flusher.is_numerical_value("2.("))

    def test_numerical_value(self):
        key = self.add_value_list("plugin", "plugin_instance_0", "type", "type_instance", "host", [float('nan')])
        self.assertFalse(key  in self.flusher.metric_map)
        self.assertTrue(key in self.flusher.nan_key_set)
        key = self.add_value_list("plugin", "plugin_instance_1", "type", "type_instance", "host", [10])
        self.assertTrue(key in self.flusher.metric_map)
        self.assertFalse(key in self.flusher.nan_key_set)
        key = self.add_value_list("plugin", "plugin_instance_1", "type", "type_instance", "host", [10])
        self.assertTrue(key in self.flusher.metric_map)
        self.assertEqual(self.flusher.metric_map[key][0].statistics.sum, 20)
        key = self.add_value_list("plugin", "plugin_instance_1", "type", "type_instance", "host", ["20aaa"])
        self.assertEqual(self.flusher.metric_map[key][0].statistics.sum, 20)
        self.assertTrue(key in self.flusher.nan_key_set)
        key = self.add_value_list("plugin", "plugin_instance_1", "type", "type_instance", "host", [-20])
        self.assertTrue(key in self.flusher.metric_map)
        self.assertEqual(self.flusher.metric_map[key][0].statistics.sum, 0)
        key = self.add_value_list("plugin", "plugin_instance_2", "type", "type_instance", "host", [10,"20aaa"])
        self.assertTrue( key in self.flusher.metric_map)
        self.assertEqual(self.flusher.metric_map[key][0].statistics.sum, 10)
        self.assertTrue(key in self.flusher.nan_key_set)
        key = self.add_value_list("plugin", "plugin_instance_2", "type", "type_instance", "host", ["20aaa", 10])
        self.assertEqual(self.flusher.metric_map[key][0].statistics.sum, 20)
        self.assertTrue(key in self.flusher.metric_map)
        self.assertTrue(key in self.flusher.nan_key_set)
        key = self.add_value_list("plugin", "plugin_instance_3", "type", "type_instance", "host", ["20aaa"])
        self.assertFalse(key in self.flusher.metric_map)
        self.assertTrue(key in self.flusher.nan_key_set)
        key = self.add_value_list("plugin", "plugin_instance_4", "type", "type_instance", "host", [20.22])
        self.assertTrue(key in self.flusher.metric_map)
        self.assertFalse(key in self.flusher.nan_key_set)

    def test_flushes_before_adding_metrics(self):
        self.flusher = Flusher(config_helper=self.config_helper, dataset_resolver=self.dataset_resolver)
        self.flusher.flush_interval_in_seconds = 0
        vl = self._get_vl_mock("CPU", "0", "CPU", "Steal", values=(50, 100, 200), timestamp=0)
        self.flusher.add_metric(vl)
        received_request = self.server_get_received_request()
        self.assertEquals(None, received_request)
        self.flusher.add_metric(vl)
        received_request = self.server_get_received_request()
        self.assertTrue(MetricDataBuilder(self.config_helper, vl)._build_metric_name() in received_request)

    def test_is_flush_time(self):
        self.flusher.flush_interval_in_seconds = 10
        self.assertFalse(self.flusher._is_flush_time(time()))
        self.flusher.flush_interval_in_seconds = 0.5
        self.assertTrue(self.flusher._is_flush_time(time() + 1))

    def test_get_metric_key_is_unique(self):
        vl1 = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10], 101.1)
        vl2 = self._get_vl_mock("plugin", "plugin_instance2", "type", "type_instance", "host", [10], 152.2)
        key = self.flusher._get_metric_key(vl1)
        self.assertEquals("plugin-plugin_instance-type-type_instance", key)
        key = self.flusher._get_metric_key(vl2)
        self.assertEquals("plugin-plugin_instance2-type-type_instance", key)

    def test_get_metric_key_is_unique_without_enable_high_resolution_metrics(self):
        self.config_helper.enable_high_resolution_metrics = True
        self.flusher = Flusher(config_helper=self.config_helper, dataset_resolver=self.dataset_resolver)
        vl1 = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10], 101.1)
        key = self.flusher._get_metric_key(vl1)
        self.assertEquals("plugin-plugin_instance-type-type_instance", key)
        vl = self._get_vl_mock("plugin", "plugin_instance_1", "type", "type_instance", "host", [10.1], 20.1)
        self.flusher._aggregate_metric(vl)
        key = self.flusher._get_metric_key(vl)
        self.assertTrue(key + "-" + str(20) in self.flusher.metric_map)
        vl = self._get_vl_mock("plugin", "plugin_instance_1", "type", "type_instance", "host", [10.1], 20.9)
        self.flusher._aggregate_metric(vl)
        key = self.flusher._get_metric_key(vl)
        self.assertTrue(key + "-" + str(20) in self.flusher.metric_map)

    def test_whitelisted_metrics_are_registered_by_flusher(self):
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10], 0)
        self.flusher.add_metric(vl)
        key = self.flusher._get_metric_key(vl)
        self.config_helper.whitelist.is_whitelisted.assert_called_with(key)
        self.assertTrue(key in self.flusher.metric_map)

    def test_not_whitelisted_metrics_are_dropped(self):
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10])
        self.config_helper.whitelist.is_whitelisted.return_value = False
        self.flusher.add_metric(vl)
        key = self.flusher._get_metric_key(vl)
        self.config_helper.whitelist.is_whitelisted.assert_called_with(key)
        self.assertFalse(key in self.flusher.metric_map)

    def test_aggregate_metric_adds_new_metrics_to_map(self):
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10], 0)
        key = self.flusher._get_metric_key(vl)
        self.assertFalse(key in self.flusher.metric_map)
        self.flusher._aggregate_metric(vl)
        self.assertTrue(key in self.flusher.metric_map)
        metric = self.flusher.metric_map[key][0]
        self._assert_statistics(metric, min=10, max=10, sum=10, sample_count=1)

    def test_aggregate_metric_adds_new_metric_to_map_and_aggregates_values(self):
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10, -10, 20, -50], 0)
        key = self.flusher._get_metric_key(vl)
        self.assertFalse(key in self.flusher.metric_map)
        self.flusher._aggregate_metric(vl)
        self.assertTrue(key in self.flusher.metric_map)
        metric = self.flusher.metric_map[key][0]
        self._assert_statistics(metric, min=-50, max=20, sum=-30, sample_count=4)

    def test_aggregate_metric_aggregates_values_with_existing_metric(self):
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10], 0)
        key = self.flusher._get_metric_key(vl)
        self.flusher._aggregate_metric(vl)
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [100, -30], 0)
        self.flusher._aggregate_metric(vl)
        metric = self.flusher.metric_map[key][0]
        self._assert_statistics(metric, min=-30, max=100, sum=80, sample_count=3)

    def test_aggregate_metric_will_drop_metrics_above_the_limit(self):
        logger = MagicMock()
        logger.warning = Mock()
        self.flusher._LOGGER = logger
        self.flusher.max_metrics_to_aggregate = 10
        for i in range(15):
            self.flusher._aggregate_metric(self._get_vl_mock("plugin" + str(i), "plugin_instance", "type", "type_instance", "host", [i], 0))
            if i < 10:
                self.assertEquals(i + 1, len(self.flusher.metric_map))
            else:
                self.assertEquals(10, len(self.flusher.metric_map))
        self.assertEquals(5, logger.warning.call_count)
        self.flusher._aggregate_metric(self._get_vl_mock("plugin1", "plugin_instance", "type", "type_instance", "host", [10], 0))
        self.assertEquals(5, logger.warning.call_count)
        self.assertEquals(10, len(self.flusher.metric_map))

    @patch('cloudwatch.modules.flusher.PutClient')
    def test_flush_if_ready(self, client_class):
        client_class.return_value = self.client
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10], 0)
        self.flusher._aggregate_metric(vl)
        self.flusher.flush_interval_in_seconds = 10
        self.flusher._flush_if_need(time())
        self.assertFalse(self.client.put_metric_data.called)
        self.flusher._flush_if_need(time() + 10)
        self.assertTrue(self.client.put_metric_data.called)

    @patch('cloudwatch.modules.flusher.PutClient')
    def test_flush_when_enable_high_resolution(self, client_class):
        client_class.return_value = self.client
        self.flusher.flush_interval_in_seconds = 10
        self.flusher.enable_high_resolution_metrics = True
        self.flusher.max_metrics_to_aggregate = 10
        vl = self._get_vl_mock("plugin", "plugin_instance", "type", "type_instance", "host", [10], 0)
        self.flusher._aggregate_metric(vl)
        self.flusher._flush_if_need(time())
        self.assertFalse(self.client.put_metric_data.called)
        self.flusher._flush_if_need(time() + 10)
        self.assertFalse(self.client.put_metric_data.called)
        self.flusher._flush_if_need(time() + 11)
        self.assertTrue(self.client.put_metric_data.called)
        self.assertEquals(1, self.client.put_metric_data.call_count)
        self.flusher.max_metrics_to_aggregate = 20
        for i in range(21):
            self.flusher._aggregate_metric(self._get_vl_mock("plugin" + str(i), "plugin_instance", "type", "type_instance", "host", [i], 0))
        self.assertEquals(2, self.client.put_metric_data.call_count)

    def test_prepare_batches_respects_the_size_limit(self):
        for i in range(self.flusher._MAX_METRICS_PER_PUT_REQUEST + 1):
            self.flusher._aggregate_metric(self._get_vl_mock("plugin" + str(i), "plugin_instance", "type", "type_instance", "host", [i], 0))
        batch = self.flusher._prepare_batch().next()
        self.assertEquals(self.flusher._MAX_METRICS_PER_PUT_REQUEST, len(list(batch)))
        batch = self.flusher._prepare_batch()
        self.assertEquals(1, len(list(batch)))
    
    @patch('cloudwatch.modules.flusher.PutClient')
    def test_flush_can_flush_metrics(self, client_class):
        client_class.return_value = self.client
        for i in range((self.flusher._MAX_METRICS_PER_PUT_REQUEST * 2) + 1):
                self.flusher._aggregate_metric(self._get_vl_mock("plugin" + str(i), "plugin_instance", "type", "type_instance", "host", [i], 0))
        self.flusher._flush()
        self.assertEquals(3, self.client.put_metric_data.call_count)
        
    @patch('cloudwatch.modules.flusher.PutClient')
    def test_flush_does_not_call_client_when_metric_map_is_empty(self, client_class):   
        client_class.return_value = self.client 
        self.flusher._flush()
        self.assertFalse(self.client.put_metric_data.called)

    def test_multivalue_metrics_set_the_type_instance(self):
        vl1 = self._get_vl_mock("plugin", "plugin_instance", "multivalue_type", "", "host", [10, 11], 101.1)
        expanded_value_list=self.flusher._expand_value_list(vl1)

        self.assertListEqual([value.type_instance for value in expanded_value_list], ['name1', 'name2'])
        self.assertListEqual([value.values for value in expanded_value_list], [[10], [11]])


    def test_multivalue_metrics_appends_the_type_instance(self):
        vl1 = self._get_vl_mock("plugin", "plugin_instance", "multivalue_type", "type_instance", "host", [10, 11], 101.1)
        expanded_value_list=self.flusher._expand_value_list(vl1)

        self.assertListEqual([value.type_instance for value in expanded_value_list], ['type_instance.name1', 'type_instance.name2'])
        self.assertListEqual([value.values for value in expanded_value_list], [[10], [11]])


    def _assert_statistics(self, metric, min, max, sum, sample_count):
        self.assertEquals(min, metric.statistics.min)
        self.assertEquals(max, metric.statistics.max)
        self.assertEquals(sum, metric.statistics.sum)
        self.assertEquals(sample_count, metric.statistics.sample_count)
        
    def _get_vl_mock(self, plugin, plugin_instance, type, type_instance, host="MockHost", values=[], timestamp=0):
        vl = MagicMock()
        vl.plugin = plugin
        vl.plugin_instance = plugin_instance
        vl.type = type
        vl.type_instance = type_instance
        vl.host = host
        vl.values = values
        vl.time = timestamp;
        return vl

    def server_get_received_request(self):
        try:
            return open(FakeServer.REQUEST_FILE).read()[2:]  # trim '/?' from the request 
        except:
            return None

    def add_value_list(self, plugin, plugin_instance, type, type_instance, host="MockHost", values=[]):
        vl = self._get_vl_mock(plugin, plugin_instance, type, type_instance, host, values)
        self.flusher._aggregate_metric(vl)
        key = self.flusher._get_metric_key(vl)
        return key

    @classmethod
    def tearDownClass(cls):
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None
