import unittest
import requests
import time

from mock import Mock, MagicMock
from cloudwatch.modules.client.ec2getclient import EC2GetClient
from cloudwatch.modules.plugininfo import PLUGIN_NAME, PLUGIN_VERSION
from helpers.fake_http_server import FakeServer
from cloudwatch.modules.awscredentials import AWSCredentials
from cloudwatch.modules.metricdata import MetricDataStatistic


class EC2GetClientTest(unittest.TestCase):

    FAKE_SERVER = None
    USER_AGENT = PLUGIN_NAME + "/" + str(PLUGIN_VERSION) 
    
    @classmethod
    def setUpClass(cls):
        cls.FAKE_SERVER = FakeServer()
        cls.FAKE_SERVER.start_server()
        cls.FAKE_SERVER.serve_forever()
        
    def setUp(self):
        self.server = EC2GetClientTest.FAKE_SERVER
        self.server.set_expected_response("OK", 200)
        self.config_helper = MagicMock()
        self.config_helper.credentials = AWSCredentials("access", "secret")
        self.config_helper.region = "localhost"
        self.config_helper.ec2_endpoint = "http://localhost:57575/"
        self.client = EC2GetClient(self.config_helper)
        self.logger = MagicMock()
        self.logger.warning = Mock()
        self.client.__class__._LOGGER = self.logger
        
    def test_constructor(self):
        connection_timeout = 10
        response_timeout = 20
        client = EC2GetClient(self.config_helper, connection_timeout, response_timeout)
        self.assertEquals("http://localhost:57575/", client.endpoint)
        self.assertEquals((connection_timeout,response_timeout), client.timeout)
    
    def test_initialize_get_client_with_valid_endpoint(self):
        self.config_helper.endpoint = "https://ec2.eu-west-1.amazonaws.com"
        self.client = EC2GetClient(self.config_helper)
    
    def test_initiialize_get_client_with_invalid_endpoint(self):
        self.config_helper.ec2_endpoint = "invalid_endpoint"
        with self.assertRaises(EC2GetClient.InvalidEndpointException):
            self.client = EC2GetClient(self.config_helper)
        self.assertTrue(self.logger.error.called)
    
    def test_get_request(self):
        request = "Testing_Request"
        result = self.client._run_request("Testing_Request")
        self.assertEquals("OK", result.text)
        self.assertEquals(200, result.status_code)
        self.assertTrue(request in self.server_get_received_request())   
        
    def test_get_request_timeout(self):
        self.server.set_timeout_delay(EC2GetClient._DEFAULT_RESPONSE_TIMEOUT * (EC2GetClient._TOTAL_RETRIES + 1))
        with self.assertRaises(requests.ConnectionError):
            self.client._run_request("request")
        self.server_restart()
        
    def test_get_autoscaling_name(self):
        instance_id = "i-1818591f"
        self.client.get_autoscaling_group(instance_id)
        received_request = self.server_get_received_request()
        self.assertTrue("Filter.1.Name=key" in received_request)
        self.assertTrue("Filter.1.Value.1=aws%3Aautoscaling%3AgroupName" in received_request)
        self.assertTrue("Filter.2.Name=resource-id" in received_request)
        self.assertTrue("Filter.2.Value.1=" + instance_id in received_request)
        self.assertTrue("Action=DescribeTags" in received_request)
        self.assertTrue("Version" in received_request)
        self.assertTrue("X-Amz-Algorithm" in received_request)
        self.assertTrue("X-Amz-Credential" in received_request)
        self.assertTrue("X-Amz-Date" in received_request)
        self.assertTrue("X-Amz-SignedHeaders" in received_request)
    
    def test_get_autoscaling_name_with_iam_role_creds(self):
        instance_id = "i-1818591f"
        self.config_helper.credentials = AWSCredentials("access", "secret", "IAM_ROLE_TOKEN")
        self.client = EC2GetClient(self.config_helper)
        self.client.get_autoscaling_group(instance_id)
        received_request = self.server_get_received_request()
        self.assertTrue("X-Amz-Security-Token=IAM_ROLE_TOKEN" in received_request)
    
    def test_get_autoscaling_name_with_retry(self):
        self.server.set_timeout_delay(EC2GetClient._DEFAULT_RESPONSE_TIMEOUT * EC2GetClient._TOTAL_RETRIES)
        instance_id = "i-1818591f"
        self.client = EC2GetClient(self.config_helper)
        self.client.get_autoscaling_group(instance_id)
        received_request = self.server_get_received_request()
        self.assertTrue("Filter.2.Value.1=" + instance_id in received_request)
        
    def test_get_autoscaling_name_with_timeout(self):
        self.server.set_timeout_delay(EC2GetClient._DEFAULT_RESPONSE_TIMEOUT * (EC2GetClient._TOTAL_RETRIES + 1))
        instance_id = "i-1818591f"
        self.client.get_autoscaling_group(instance_id)
        self.assertTrue(self.logger.warning.called)
     
    def test_get_user_agent_header(self):
        header = self.client._get_user_agent_header()
        self.assertTrue(EC2GetClientTest.USER_AGENT in header)
     
    def test_get_custom_headers(self):
        headers = self.client._get_custom_headers()
        self.assertTrue(headers['User-Agent'])
        self.assertTrue(EC2GetClientTest.USER_AGENT in headers['User-Agent'])
    
    def test_server_received_user_agent_information(self):
        instance_id = "i-1818591f"
        self.client.get_autoscaling_group(instance_id)
        received_request = self.server_get_received_request()
        self.assertTrue(EC2GetClientTest.USER_AGENT in received_request)
        
    def test_client_raise_exception_on_credentials_error(self):    
        instance_id = "i-1818591f"
        self.server.set_expected_response("Client Error: Forbidden", 403)
        self.assert_no_retry_on_error_request(instance_id)
    
    def test_client_raise_exception_on_service_unavailable_error(self):    
        instance_id = "i-1818591f"
        self.server.set_expected_response("Service Unavailable", 503)
        self.assert_no_retry_on_error_request(instance_id)
    
    def test_client_raise_exception_on_request_throttling(self):    
        instance_id = "i-1818591f"
        self.server.set_expected_response("Request Throttled", 400)
        self.assert_no_retry_on_error_request(instance_id)
        
    def test_credentials_are_updated_in_the_get_client(self):
        instance_id = "i-1818591f"
        self.client.get_autoscaling_group(instance_id)
        received_request = self.server_get_received_request()
        self.assertTrue("access" in received_request)
        self.config_helper.credentials = AWSCredentials("NEW_ACCESS_KEY", "NEW_SECRET_KEY")
        self.client = EC2GetClient(self.config_helper)
        self.client.get_autoscaling_group(instance_id)
        received_request = self.server_get_received_request()
        self.assertTrue("NEW_ACCESS_KEY" in received_request)
        
    def assert_no_retry_on_error_request(self, instance_id):
        start = time.time()
        self.client.get_autoscaling_group(instance_id)
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
        return open(FakeServer.REQUEST_FILE).read()[2:] # trim '/?' from the request 
        
    @classmethod
    def tearDownClass(cls):    
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None

