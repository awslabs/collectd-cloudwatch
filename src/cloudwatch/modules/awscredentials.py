class AWSCredentials(object):
    """
    The AWSCredentials object encapsulates the credentials used for signing put requests.
    
    Keyword arguments:
    access_key -- the AWS access key ID  (default None)
    secret_key -- the AWS secret key (default None)
    token -- the temporary security token obtained through a call to 
             AWS Security Token Service when using IAM Role (default None)
    """

    def __init__(self, access_key=None, secret_key=None, token=None):
        self.access_key = access_key
        self.secret_key = secret_key
        self.token = token
