import unittest
import requests
import time

from requests.utils import quote
from mock import Mock, MagicMock
from cloudwatch.modules.client.stsassumeroleclient import StsAssumRoleClient
from cloudwatch.modules.plugininfo import PLUGIN_NAME, PLUGIN_VERSION
from helpers.fake_http_server import FakeServer
from cloudwatch.modules.awscredentials import AWSCredentials

class StsAssumRoleClientTest(unittest.TestCase):
    
    FAKE_SERVER = None
    USER_AGENT = PLUGIN_NAME + "/" + str(PLUGIN_VERSION)
    XML_RESPONSE = '''
        <AssumeRoleResponse xmlns='https://sts.amazonaws.com/doc/2011-06-15/'>
            <AssumeRoleResult>
                <Credentials>
                  <SessionToken>token_test</SessionToken>
                  <SecretAccessKey>secret_key_test</SecretAccessKey>
                  <Expiration>2011-07-15T23:28:33.359Z</Expiration>
                  <AccessKeyId>access_key_test</AccessKeyId>
                </Credentials>
            </AssumeRoleResult>
        </AssumeRoleResponse>
        '''
    
    @classmethod
    def setUpClass(cls):
        cls.FAKE_SERVER = FakeServer()
        cls.FAKE_SERVER.start_server()
        cls.FAKE_SERVER.serve_forever()
        
    def setUp(self):
        self.server = StsAssumRoleClientTest.FAKE_SERVER
        self.server.set_expected_response(StsAssumRoleClientTest.XML_RESPONSE, 200)
        self.client = StsAssumRoleClient(AWSCredentials("access", "secret"), "http://localhost:57575/", "localhost")
        self.logger = MagicMock()
        self.logger.warning = Mock()
        self.client.__class__._LOGGER = self.logger
    
    def server_restart(self):
        self.server.stop_server()
        self.server.start_server()
        self.server.set_expected_response(StsAssumRoleClientTest.XML_RESPONSE, 200)
        self.server.serve_forever()
    
    def server_get_received_request(self):
        return open(FakeServer.REQUEST_FILE).read()[2:] # trim '/?' from the request 
        
    @classmethod
    def tearDownClass(cls):    
        cls.FAKE_SERVER.stop_server()
        cls.FAKE_SERVER = None
    
    def test_constructor(self):
        connection_timeout = 10
        response_timeout = 20
        client = StsAssumRoleClient(AWSCredentials("access", "secret"), "http://localhost:57575/", "localhost", connection_timeout=connection_timeout, response_timeout=response_timeout)
        self.assertEquals("http://localhost:57575/", client.endpoint)
        self.assertEquals((connection_timeout,response_timeout), client.timeout)
    
    def test_initialize_sts_assume_role_with_valid_endpoint(self):
        self.client = StsAssumRoleClient(AWSCredentials("access", "secret"), "https://sts.eu-west-1.amazonaws.com", "localhost")
    
    def test_put_initialize_sts_assume_role_with_invalid_endpoint(self):
        with self.assertRaises(StsAssumRoleClient.InvalidEndpointException):
            self.client = StsAssumRoleClient(AWSCredentials("access", "secret"), "invalid_endpoint", "localhost")
        self.assertTrue(self.logger.error.called)
    
    def test_get_user_agent_header(self):
        header = self.client._get_user_agent_header()
        self.assertTrue(StsAssumRoleClientTest.USER_AGENT in header)
    
    def test_get_custom_headers(self):
        headers = self.client._get_custom_headers()
        self.assertTrue(headers['User-Agent'])
        self.assertTrue(StsAssumRoleClientTest.USER_AGENT in headers['User-Agent'])
    
    def test_get_request(self):
        request = "Testing_Request"
        self.server.set_expected_response("OK", 200)
        result = self.client._run_request("Testing_Request")
        self.assertEquals("OK", result.text)
        self.assertEquals(200, result.status_code)
        self.assertTrue(request in self.server_get_received_request())   
        
    def test_client_raise_exception_on_credentials_error(self):    
        self.server.set_expected_response("Client Error: Forbidden", 403)
        self.assert_no_retry_on_error_request("arn_role_test", "arn_session_name_test", 3600)
    
    def test_client_raise_exception_on_service_unavailable_error(self):    
        self.server.set_expected_response("Service Unavailable", 503)
        self.assert_no_retry_on_error_request("arn_role_test", "arn_session_name_test", 3600)
    
    def test_client_raise_exception_on_request_throttling(self):    
        self.server.set_expected_response("Request Throttled", 400)
        self.assert_no_retry_on_error_request("arn_role_test", "arn_session_name_test", 3600)
        
    def test_server_received_user_agent_information(self):
        self.client.get_credentials("arn_role_test", "arn_session_name_test", 3600)
        received_request = self.server_get_received_request()
        self.assertTrue(StsAssumRoleClientTest.USER_AGENT in received_request)
    
    def test_get_crendetials_with_iam_role_creds(self):
        self.client = StsAssumRoleClient(AWSCredentials("access", "secret", "IAM_ROLE_TOKEN"), "http://localhost:57575/", "localhost")
        self.client.get_credentials("arn_role_test", "arn_session_name_test", 3600)
        received_request = self.server_get_received_request()
        self.assertTrue("X-Amz-Security-Token=IAM_ROLE_TOKEN" in received_request)
    
    def test_get_crendetials_with_retry(self):
        self.server.set_timeout_delay(StsAssumRoleClient._DEFAULT_RESPONSE_TIMEOUT * StsAssumRoleClient._TOTAL_RETRIES)
        self.client = StsAssumRoleClient(AWSCredentials("access", "secret"), "http://localhost:57575/", "localhost")
        self.client.get_credentials("arn_role_test", "arn_session_name_test", 3600)
        received_request = self.server_get_received_request()
        self.assertTrue("RoleArn" in received_request)
        
    def test_get_crendetials(self):
        arn_role = "sample_arn_role"
        duration_seconds = "3600"
        role_session_name = "test_session_name"
        self.client.get_credentials(arn_role, role_session_name, duration_seconds)
        received_request = self.server_get_received_request()
        self.assertTrue("RoleSessionName=" + role_session_name in received_request)
        self.assertTrue("RoleArn=" + arn_role in received_request)
        self.assertTrue("DurationSeconds=" + duration_seconds in received_request)
        self.assertTrue("Action=AssumeRole" in received_request)
        self.assertTrue("Version" in received_request)
        self.assertTrue("X-Amz-Algorithm" in received_request)
        self.assertTrue("X-Amz-Credential" in received_request)
        self.assertTrue("X-Amz-Date" in received_request)
        self.assertTrue("X-Amz-SignedHeaders" in received_request)
        self.assertTrue("X-Amz-Signature" in received_request)
    
    def test_get_crendetials_valid_response(self):
        session_token = 'AQoDYXdzEPT//////////wEXAMPLEtc764bNrC9SAPBSM22wDOk4x4HIZ8j4FZTwdQWLWsKWHGBuFqwAeMicRXmxfpSPfIeoIYRqTflfKD8YUuwthAx7mSEI/qkPpKPi/kMcGd+xo0rKwT38xVqr7ZD0u0iPPkUL64lIZbqBAz+scqKmlzm8FDrypNC9Yjc8fPOLn9FX9KSYvKTr4rvx3iSIlTJabIQwj2ICCR/oLxBA=='
        expected_credential = AWSCredentials('AKIAIOSFODNN7EXAMPLE', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY', session_token)
        arn_role = "sample_arn_role"
        duration_seconds = "3600"
        role_session_name = "test_session_name"
        resp_content = '''
        <AssumeRoleResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
          <AssumeRoleResult>
            <Credentials>
              <SessionToken>
              ''' + expected_credential.token + ''' 
              </SessionToken>
              <SecretAccessKey>
               ''' + expected_credential.secret_key + '''
              </SecretAccessKey>
              <Expiration>2011-07-15T23:28:33.359Z</Expiration>
              <AccessKeyId>
              ''' + expected_credential.access_key + '''
              </AccessKeyId>
            </Credentials>
            <AssumedRoleUser>
              <Arn>
                ''' + arn_role + '''
              </Arn>
              <AssumedRoleId>ARO123EXAMPLE123:Bob</AssumedRoleId>
            </AssumedRoleUser>
            <PackedPolicySize>6</PackedPolicySize>
          </AssumeRoleResult>
          <ResponseMetadata>
            <RequestId>c6104cbe-af31-11e0-8154-cbc7ccf896c7</RequestId>
          </ResponseMetadata>
        </AssumeRoleResponse>
        '''
        self.server.set_expected_response(resp_content, 200)
        cred = self.client.get_credentials(arn_role, role_session_name, duration_seconds)
        self.assertTrue(expected_credential.access_key == cred.access_key)
        self.assertTrue(expected_credential.secret_key == cred.secret_key)
        self.assertTrue(expected_credential.token == cred.token)
            
    
    def test_get_crendetials_with_timeout(self):
        self.server.set_timeout_delay(StsAssumRoleClient._DEFAULT_RESPONSE_TIMEOUT * (StsAssumRoleClient._TOTAL_RETRIES + 1))
        self.assertRaises(ValueError, self.client.get_credentials, "arn_role_test", "arn_session_name_test", 3600)
        self.assertTrue(self.logger.warning.called)
    
    def test_get_request_timeout(self):
        self.server.set_timeout_delay(StsAssumRoleClient._DEFAULT_RESPONSE_TIMEOUT * (StsAssumRoleClient._TOTAL_RETRIES + 1))
        with self.assertRaises(requests.ConnectionError):
            self.client._run_request("request")
        self.server_restart()
    
    def assert_no_retry_on_error_request(self, arn_role, role_session_name, duration_seconds):
        start = time.time()
        self.assertRaises(ValueError, self.client.get_credentials, arn_role, role_session_name, duration_seconds)
        end = time.time()
        delta = end - start
        self.assertTrue(delta < self.client._DEFAULT_RESPONSE_TIMEOUT)
        self.assertTrue(self.logger.warning.called)
