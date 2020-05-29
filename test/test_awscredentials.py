import unittest
from cloudwatch.modules.awscredentials import AWSCredentials


class AWSCredentialsTest(unittest.TestCase):
   
    def test_aws_credentials_with_default_constructor(self):
        creds = AWSCredentials()
        assert_credentials_data(creds)
        
    def test_aws_credentials_with_custom_values(self):
        new_access_key = "accessKey"
        new_secret_key = "secretKey"
        new_token = "token"
        credentials = AWSCredentials(new_access_key, new_secret_key, new_token)
        assert_credentials_data(credentials, new_access_key, new_secret_key, new_token)


def assert_credentials_data(credentials, access_key=None, secret_key=None, token=None):
    assert access_key == credentials.access_key
    assert secret_key == credentials.secret_key
    assert token == credentials.token
