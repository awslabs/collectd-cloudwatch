import unittest
from cloudwatch.modules.awscredentials import AWSCredentials, AWS_CREDENTIALS_TIMEFORMAT
from datetime import datetime, timedelta

class AWSCredentialsTest(unittest.TestCase):
    
    def test_aws_credentials_with_default_constructor(self):
        creds = AWSCredentials()
        assert_credentials_data(creds)
        
    def test_aws_credentials_with_custom_values(self):
        new_access_key = "accessKey"
        new_secret_key = "secretKey"
        new_token = "token"
        new_expire_at_str = '2012-12-03T20:48:03Z'
        new_expire_at = datetime.strptime(new_expire_at_str, AWS_CREDENTIALS_TIMEFORMAT)
        
        credentials = AWSCredentials(new_access_key, new_secret_key, new_token, new_expire_at_str)
        assert_credentials_data(credentials, new_access_key, new_secret_key, new_token, new_expire_at)
    
    def test_aws_credentials_exception_invalid_expire_time(self):
        with self.assertRaises(ValueError):
            AWSCredentials(expire_at='2012-12-03T20:48:_invalid_03Z')
    
    def test_aws_credentials_is_expired(self):
        already_expired = datetime.utcnow() - timedelta(hours=1)
        cred = AWSCredentials(expire_at=already_expired.strftime(AWS_CREDENTIALS_TIMEFORMAT))
        self.assertTrue(cred.is_expired())
        
    def test_aws_credentials_is_not_expired(self):
        already_expired = datetime.utcnow() + timedelta(hours=1)
        cred = AWSCredentials(expire_at=already_expired.strftime(AWS_CREDENTIALS_TIMEFORMAT))
        self.assertFalse(cred.is_expired())
    
    def test_aws_credentials_is_not_expired_on_NONE(self):
        cred = AWSCredentials()
        self.assertFalse(cred.is_expired())
        
def assert_credentials_data(credentials, access_key=None, secret_key=None, token=None, expire_at=None):
    assert access_key == credentials.access_key
    assert secret_key == credentials.secret_key
    assert token == credentials.token
    assert expire_at == credentials.expire_at
    
