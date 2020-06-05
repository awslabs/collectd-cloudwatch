import unittest

from cloudwatch.modules.awscredentials import AWSCredentials
from cloudwatch.modules.awsutils import get_aws_timestamp
from cloudwatch.modules.client.signer import Signer


class SignerTest(unittest.TestCase):
    
    def setUp(self):
        self.credentials = AWSCredentials("access_key", "secret_key")
        self.region = "test_region"
        self.service = "monitoring"
        self.algorithm = "AWS4-HMAC-SHA256"
        self.signer = Signer(self.credentials, self.region, self.service, self.algorithm)
    
    def test_get_string_to_sign_sequence(self):
        timestamp = get_aws_timestamp()
        credential_scope = "testing/credential/scope"
        canonical_request = "testing&canonical&request"
        string_to_sign = self.signer._build_string_to_sign(timestamp, credential_scope, canonical_request)
        expected_string_to_sign = self.algorithm + "\n" + timestamp + "\n" + credential_scope + "\n" + self.signer._hash(canonical_request)
        self.assertEquals(expected_string_to_sign, string_to_sign)

    def test_get_canonical_request_sequence(self):
        method = "GET"
        uri = "/"
        query_string = "testing&querystring"
        canonical_headers = "host"
        signed_headers = "host"
        payload = ""
        expected_request = method + "\n" + uri + "\n" + query_string + "\n" + canonical_headers + "\n" \
            + signed_headers + "\n" + self.signer._hash(payload)
        generated_request = self.signer._build_canonical_request(query_string, canonical_headers, signed_headers, payload)
        self.assertEquals(expected_request, generated_request)

    # regression tests
    def test_hash(self):
        signer = self.get_regression_signer()
        test_data = "test data string"
        historical_result = "8b309d12587350c3288dbca5a859346f52631ebc7145d5c9c1781ea84dec0c82"
        self.assertEquals(historical_result, signer._hash(test_data))
   
    def test_sign(self):
        signer = self.get_regression_signer()
        data = "testing&canonical&request"
        historical_result = b"\xfb\xd2\x86\x87&\xdaC\x03\x98\x9dIC\xcbP?\xa8\\\xfeJ\x82\x03\xe6w\xd4\x963Q\xfd\xe5-\xdb\xcf"
        self.assertEquals(historical_result, signer._sign(signer.credentials.secret_key, data))
        
    def test_build_signature_key(self):
        signer = self.get_regression_signer()
        datestamp = "20150725"
        historical_result = b"=7\xa5&\xa3%\xd5Q\x9a\x1ah\xee2mSw<\xdd\xf8\x0e\xde\xdf5\x94\xa6(M`\x00\xd1\x81\xea"
        new_result = signer._build_signature_key(signer.credentials.secret_key, datestamp, signer.region, signer.service)
        self.assertEquals(historical_result, new_result)
        
    def test_create_request_signature(self):
        signer = self.get_regression_signer()
        canonical_querystring = "Action=PutMetricData&Version=2010-08-01&Namespace=TestNamespace&" \
            "MetricData.member.1.MetricName=buffers&MetricData.member.1.Unit=Bytes&MetricData.member.1.Value=231434333" \
            "&MetricData.member.1.Dimensions.member.1.Name=InstanceType&MetricData.member.1.Dimensions.member.1.Value=m1.small"
        credential_scope = "20150725/eu-west-1/monitoring/aws4_request"
        aws_timestamp = "20150725T113000Z"
        datestamp = "20150725"
        canonical_headers = "host:monitoring.eu-west-1.amazonaws.com\n"
        signed_headers = "host"
        payload = ""
        historical_result = "7ad2788349d53dee9ad212eaf6063134a9f0a9e40de26a346f6aaea750c811de"
        new_result = signer.create_request_signature(canonical_querystring, credential_scope, aws_timestamp, datestamp, canonical_headers, signed_headers, payload)
        self.assertEquals(historical_result, new_result)
        
    def get_regression_signer(self):
        # Warning: changing any of these parameters here will cause regression tests to fail!
        self.credentials = AWSCredentials("access_key", "secret_key")
        self.region = "eu-west-1"
        self.service = "monitoring"
        self.algorithm = "AWS4-HMAC-SHA256"
        return Signer(self.credentials, self.region, self.service, self.algorithm)
