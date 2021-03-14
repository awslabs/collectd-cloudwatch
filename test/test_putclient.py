import unittest
import requests
import time

from mock import Mock, MagicMock
from cloudwatch.modules.client.putclient import PutClient
from cloudwatch.modules.plugininfo import PLUGIN_NAME, PLUGIN_VERSION
from helpers.fake_http_server import FakeServer
from cloudwatch.modules.awscredentials import AWSCredentials
from cloudwatch.modules.metricdata import MetricDataStatistic


class PutClientTest(unittest.TestCase):

    FAKE_SERVER = None
    USER_AGENT = PLUGIN_NAME + "/" + str(PLUGIN_VERSION) 
    
    @classmethod
    def setUpClass(cls):
        cls.FAKE_SERVER = FakeServer()
        cls.FAKE_SERVER.start_server()
        cls.FAKE_SERVER.serve_forever()
        
    def setUp(self):
        self.server = PutClientTest.FAKE_SERVER
        self.server.set_expected_response("OK", 200)
        self.config_helper = MagicMock()
        self.config_helper.credentials = AWSCredentials("access", "secret")
        self.config_helper.region = "localhost"
        self.config_helper.endpoint = "http://localhost:57575/"
        self.client = PutClient(self.config_helper)
        self.logger = MagicMock()
        self.logger.warning = Mock()
        self.client.__class__._LOGGER = self.logger
        
    def test_constructor(self):
        connection_timeout = 10
        response_timeout = 20
        client = PutClient(self.config_helper, connection_timeout, response_timeout)
        self.assertEquals("http://localhost:57575/", client.endpoint)
        self.assertEquals((connection_timeout,response_timeout), client.timeout)
    
    def test_initialize_put_client_with_valid_endpoint(self):
        self.config_helper.endpoint = "https://monitoring.eu-west-1.amazonaws.com"
        self.client = PutClient(self.config_helper)
    
    def test_put_initiialize_put_client_with_invalid_endpoint(self):
        self.config_helper.endpoint = "invalid_endpoint"
        with self.assertRaises(PutClient.InvalidEndpointException):
            self.client = PutClient(self.config_helper)
        self.assertTrue(self.logger.error.called)
    
    def test_get_request(self):
        request = "Testing_Request"
        result = self.client._run_request("Testing_Request")
        self.assertEquals("OK", result.text)
        self.assertEquals(200, result.status_code)
        self.assertTrue(request in self.server_get_received_request())   
        
    def test_get_request_timeout(self):
        self.server.set_timeout_delay(PutClient._DEFAULT_RESPONSE_TIMEOUT * (PutClient._TOTAL_RETRIES + 1))
        with self.assertRaises(requests.ConnectionError):
            self.client._run_request("request")
        self.server_restart()
        
    def test_put_metric_data(self):
        metric_name = "test_metric"
        namespace = "testing_namespace"
        metric = MetricDataStatistic(metric_name, statistic_values=MetricDataStatistic.Statistics(20), namespace=namespace)
        self.client.put_metric_data(namespace, [metric])
        received_request = self.server_get_received_request()
        self.assertTrue("MetricData.member.1.MetricName=" + metric_name in received_request)
        self.assertTrue("MetricData.member.1.Timestamp=" + metric.timestamp in received_request)
        self.assertTrue("MetricData.member.1.StatisticValues." in received_request)
        self.assertTrue("Namespace=" + namespace in received_request)
        self.assertTrue("Action=PutMetricData" in received_request)
        self.assertTrue("Version" in received_request)
        self.assertTrue("X-Amz-Algorithm" in received_request)
        self.assertTrue("X-Amz-Credential" in received_request)
        self.assertTrue("X-Amz-Date" in received_request)
        self.assertTrue("X-Amz-SignedHeaders" in received_request)
    
    def test_put_metric_data_with_iam_role_creds(self):
        metric_name = "test_metric"
        namespace = "testing_namespace"
        metric = MetricDataStatistic(metric_name, statistic_values=MetricDataStatistic.Statistics(20), namespace=namespace)
        self.config_helper.credentials = AWSCredentials("access", "secret", "IAM_ROLE_TOKEN")
        self.client = PutClient(self.config_helper)
        self.client.put_metric_data(namespace, [metric])
        received_request = self.server_get_received_request()
        self.assertTrue("X-Amz-Security-Token=IAM_ROLE_TOKEN" in received_request)
    
    def test_put_metric_data_with_retry(self):
        self.server.set_timeout_delay(PutClient._DEFAULT_RESPONSE_TIMEOUT * PutClient._TOTAL_RETRIES)
        metric_name = "test_metric"
        metric = MetricDataStatistic(metric_name, statistic_values=MetricDataStatistic.Statistics(20))
        self.client.put_metric_data(MetricDataStatistic.NAMESPACE, [metric])
        received_request = self.server_get_received_request()
        self.assertTrue("MetricData.member.1.MetricName=" + metric_name in received_request)
        
    def test_put_metric_data_with_timeout(self):
        self.server.set_timeout_delay(PutClient._DEFAULT_RESPONSE_TIMEOUT * (PutClient._TOTAL_RETRIES + 1))
        metric_name = "test_metric"
        metric = MetricDataStatistic(metric_name, statistic_values=MetricDataStatistic.Statistics(20))
        self.client.put_metric_data(MetricDataStatistic.NAMESPACE, [metric])
        self.assertTrue(self.logger.warning.called)
        
    def test_put_metric_data_with_inconsistent_namespaces(self):
        metric1 = MetricDataStatistic("metric_name1", statistic_values=MetricDataStatistic.Statistics(20), namespace="namespace1")
        metric2 = MetricDataStatistic("metric_name2", statistic_values=MetricDataStatistic.Statistics(20))
        with self.assertRaises(ValueError):
            self.client.put_metric_data(MetricDataStatistic.NAMESPACE, [metric1, metric2])
     
    def test_get_user_agent_header(self):
        header = self.client._get_user_agent_header()
        self.assertTrue(PutClientTest.USER_AGENT in header)
     
    def test_get_custom_headers(self):
        headers = self.client._get_custom_headers()
        self.assertTrue(headers['User-Agent'])
        self.assertTrue(PutClientTest.USER_AGENT in headers['User-Agent'])
    
    def test_server_received_user_agent_information(self):
        metric = MetricDataStatistic(metric_name="test_metric", statistic_values=MetricDataStatistic.Statistics(20), namespace="testing_namespace")
        self.client.put_metric_data("testing_namespace", [metric])
        received_request = self.server_get_received_request()
        self.assertTrue(PutClientTest.USER_AGENT in received_request)
        
    def test_client_raise_exception_on_credentials_error(self):    
        metric = MetricDataStatistic("metric_name", statistic_values=MetricDataStatistic.Statistics(20), namespace="namespace")
        self.server.set_expected_response("Client Error: Forbidden", 403)
        self.assert_no_retry_on_error_request("namespace", [metric])
    
    def test_client_raise_exception_on_service_unavailable_error(self):    
        metric = MetricDataStatistic("metric_name", namespace="namespace")
        metric.add_value(10)
        self.server.set_expected_response("Service Unavailable", 503)
        self.assert_no_retry_on_error_request("namespace", [metric])
    
    def test_client_raise_exception_on_request_throttling(self):    
        metric = MetricDataStatistic("metric_name", statistic_values=MetricDataStatistic.Statistics(20), namespace="namespace")
        self.server.set_expected_response("Request Throttled", 400)
        self.assert_no_retry_on_error_request("namespace", [metric])
        
    def test_credentials_are_updated_in_the_put_client(self):
        metric = MetricDataStatistic(metric_name="test_metric", statistic_values=MetricDataStatistic.Statistics(20), namespace="testing_namespace")
        self.client.put_metric_data("testing_namespace", [metric])
        received_request = self.server_get_received_request()
        self.assertTrue("access" in received_request)
        self.config_helper.credentials = AWSCredentials("NEW_ACCESS_KEY", "NEW_SECRET_KEY")
        self.client = PutClient(self.config_helper)
        self.client.put_metric_data("testing_namespace", [metric])
        received_request = self.server_get_received_request()
        self.assertTrue("NEW_ACCESS_KEY" in received_request)
        
    def assert_no_retry_on_error_request(self, namespace, metric_list):
        start = time.time()
        self.client.put_metric_data(namespace, metric_list)
        end = time.time()
        delta = end - start
        self.assertTrue(delta < self.client._DEFAULT_RESPONSE_TIMEOUT)
        self.assertTrue(self.logger.warning.called)    
        
    def server_restart(self):
        self.server.stop_server()
        self.server.start_server()
        self.server.set_expected_response("OK", 200)
        self.server.serve_forever()

    def server_get_received_request(self):
        return open(FakeServer.REQUEST_FILE).read()[2:]  # trim '/?' from the request
        
    @classmethod
    def tearDownClass(cls):    
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None
