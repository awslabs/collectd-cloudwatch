from datetime import datetime

AWS_CREDENTIALS_TIMEFORMAT = '%Y-%m-%dT%H:%M:%SZ'

class AWSCredentials(object):
    """
    The AWSCredentials object encapsulates the credentials used for signing put requests.
    
    Keyword arguments:
    access_key -- the AWS access key ID  (default None)
    secret_key -- the AWS secret key (default None)
    token -- the temporary security token obtained through a call to 
             AWS Security Token Service when using IAM Role (default None)
    expire_at -- The date string in ISO 8601 standard format(YYYYMMDDThhmmssZ) 
             on which the current credentials expire (default None, means never)
    """
    
    def __init__(self, access_key=None, secret_key=None, token=None, expire_at=None):
        
        self.access_key = access_key
        self.secret_key = secret_key
        self.token = token
        
        if expire_at:
            self.expire_at = datetime.strptime(expire_at, AWS_CREDENTIALS_TIMEFORMAT)
        else:
            self.expire_at = None
    
    def is_expired(self):
        """ True if credentials has been expired """
        now = datetime.utcnow()
        return self.expire_at and self.expire_at < now
            
        
