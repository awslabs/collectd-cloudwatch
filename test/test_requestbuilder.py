import unittest

from cloudwatch.modules.awscredentials import AWSCredentials
from cloudwatch.modules.awsutils import get_datestamp
from cloudwatch.modules.client.requestbuilder import RequestBuilder
from cloudwatch.modules.metricdata import MetricDataStatistic
from cloudwatch.modules.client.querystringbuilder import QuerystringBuilder#

class RequestBuilderTest(unittest.TestCase):
    
    def setUp(self):
        self.region = "test_region"
        self.namespace = "test_namespace"
        self.credentials = AWSCredentials("access_key", "secret_key")
        self.builder = RequestBuilder(self.credentials, self.region, "10")
        
    def test_get_host(self):
        self.assertEquals("monitoring." + self.region +".amazonaws.com", self.builder._get_host())
    
    def test_get_host_for_localhost_region(self):
        self.builder.region = "localhost"
        self.assertEquals("localhost", self.builder._get_host())
    
    def test_get_signed_headers(self):
        self.assertEquals("host", self.builder._get_signed_headers())
    
    def test_get_canonical_headers(self):
        headers = self.builder._get_canonical_headers()
        self.assertTrue("\n" in headers)
        self.assertTrue("host:monitoring." + self.region +".amazonaws.com\n" in headers)
        
    def test_get_credential_scope(self):
        datestamp = get_datestamp()
        v4_terminator = "aws4_request"
        service = "monitoring"
        self.builder.create_signed_request(self.namespace, [])
        self.assertEquals(datestamp + "/" + self.region + "/" + service + "/" + v4_terminator, \
                          self.builder._get_credential_scope())
    
    def test_get_credential_scope_before_geting_request(self):
        with self.assertRaises(TypeError):
            self.builder._get_credential_scope()
    
    def test_create_signed_request_generates_all_required_parameters(self):
        metric = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20))
        request = self.builder.create_signed_request(self.namespace, [metric])
        self.assertTrue("Action" in request)
        self.assertTrue("MetricData.member.1." in request)
        self.assertTrue("Namespace" in request)
        self.assertTrue("Version" in request)
        self.assertTrue("X-Amz-Algorithm" in request)
        self.assertTrue("X-Amz-Credential" in request)
        self.assertTrue("X-Amz-Date" in request)
        self.assertTrue("X-Amz-SignedHeaders" in request)
        
    def test_create_signed_request_with_iam_role_has_token_parameter(self):
        self.builder = RequestBuilder(AWSCredentials("access_key", "secret_key", "token"), self.region, "10")
        metric = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20))
        request = self.builder.create_signed_request(self.namespace, [metric])
        self.assertTrue("X-Amz-Security-Token" in request)
        
    def test_canonical_querystring_is_directly_created_by_querystring_builder(self):
        self.builder._init_timestamps()
        querystring_builder = QuerystringBuilder("10")
        metric = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20))
        original_querystring = querystring_builder.build_querystring([metric], self.builder._get_request_map())
        generated_querystring = self.builder._create_canonical_querystring([metric])
        self.assertEquals(original_querystring, generated_querystring)