import unittest
import requests

from helpers.fake_http_server import FakeServer


class FakeServerTest(unittest.TestCase):

    SERVER = None

    @classmethod
    def setUpClass(cls):
        cls.SERVER = FakeServer()
        cls.SERVER.start_server()
        cls.SERVER.serve_forever()

    def setUp(self):
        self.server = FakeServerTest.SERVER

    def test_is_server_alive(self):
        self.assertTrue(self.server.is_alive())
        self.assertTrue(self.server.is_ready_to_process())
    
    def test_server_process_forever(self):     
        self.assertTrue(self.server.is_ready_to_process())
        send_and_check_request(self.server.get_url(), "request1")
        self.assertTrue(self.server.is_ready_to_process())
        send_and_check_request(self.server.get_url(), "request2")
        self.assertTrue(self.server.is_ready_to_process())
    
    def test_server_overlapped_listeners(self):
        self.assertTrue(self.server.is_ready_to_process())
        self.assertRaises(FakeServer.ServerStateException, self.server.serve_once)
        self.assertRaises(FakeServer.ServerStateException, self.server.serve_forever)
        
    def test_server_start_overlapped_instances(self):
        self.assertRaises(FakeServer.ServerStateException, self.server.start_server)
        
    def test_timeout_triggers_only_once_per_call(self):
        timeout = 0.3
        self.server.set_timeout_delay(timeout)
        with self.assertRaises(requests.exceptions.ReadTimeout):
            requests.get(self.server.get_url(), timeout=timeout)
        requests.get(self.server.get_url(), timeout=timeout)
    
    def test_server_stop_multiple_times(self):
        self.server.stop_server()
        self.assertRaises(FakeServer.ServerStateException, self.server.stop_server)
        self.server.start_server()
        self.server.serve_forever()
    
    def test_set_custom_response(self):
        expected_response = "Expected Response"
        expected_response_code = 404
        self.server.set_expected_response(expected_response, expected_response_code)
        response = requests.get(self.server.get_url() + "request")
        self.assertEquals(expected_response, response.text)
        self.assertEquals(expected_response_code, response.status_code)
    
    @classmethod
    def tearDownClass(cls):
        try:
            cls.SERVER.stop_server()
        except:
            pass


def send_and_check_request(url, request):
    url = url + request
    response = requests.get(url)
    received_request = open(FakeServer.REQUEST_FILE).read()
    assert request in received_request[1:] # skip first character which always is '/'
    assert response.status_code == FakeServer.DEFAULT_RESPONSE_CODE
    assert response.text == FakeServer.DEFAULT_RESPONSE
