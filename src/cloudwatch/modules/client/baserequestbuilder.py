from ..awsutils import get_aws_timestamp, get_datestamp
from signer import Signer
from querystringbuilder import QuerystringBuilder

class BaseRequestBuilder(object):
    """
    The base request builder is just the in common things a request builder needs
    
    Keyword arguments:
    credentials -- The AWSCredentials object containing access and secret keys
    region -- The region to which we're targeting
    service -- The AWS Service API name
    action -- The action we'll be calling
    api_version -- The AWS specified API version.
    """

    _ALGORITHM = "AWS4-HMAC-SHA256"
    _V4_TERMINATOR = "aws4_request"
    
    def __init__(self, credentials, region, service, action, api_version, enable_high_resolution_metrics=False):
        self.credentials = credentials
        self.region = region
        self.datestamp = None
        self.service = service
        self.action = action
        self.api_version = api_version
        self.aws_timestamp = None
        self.payload = ""  # for HTTP GET payload is always empty
        self.querystring_builder = QuerystringBuilder(enable_high_resolution_metrics)
        self.signer = Signer(credentials, region, self.service, self._ALGORITHM)

    def _init_timestamps(self):
        """ Initializes timestamp and datestamp values """ 
        self.datestamp = get_datestamp()
        self.aws_timestamp = get_aws_timestamp()
    
    def _get_credential_scope(self):
        """ Builds credential scope string used in querystring and signing """
        return self.datestamp + '/' + self.region + '/' + self.service + '/' + self._V4_TERMINATOR
                  
    def _get_canonical_headers(self):
        """ Returns a list of canonical headers separated with new line characters """ 
        return "host:" + self._get_host() + "\n"
    
    def _get_signed_headers(self):
        """ Returns comma delimited list of signed headers """
        return "host"

    def _get_request_map(self):
        """
        Creates a map of request parameters and values which can be used 
        to build a canonical querystring 
        """
        canonical_map = {
            "Action": self.action,
            "Version": self.api_version,
            "X-Amz-Algorithm": self._ALGORITHM,
            "X-Amz-Credential": self.credentials.access_key + '/' + self._get_credential_scope(),
            "X-Amz-Date": self.aws_timestamp,
            "X-Amz-SignedHeaders": self._get_signed_headers()
        }
        if self.credentials.token:
            canonical_map["X-Amz-Security-Token"] = self.credentials.token
        return canonical_map