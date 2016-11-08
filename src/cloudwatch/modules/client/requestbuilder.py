from ..awsutils import get_aws_timestamp, get_datestamp
from querystringbuilder import QuerystringBuilder
from signer import Signer


class RequestBuilder(object):
    """
    The request builder is responsible for building the PutMetricData requests using HTTP GET. 
    
    Keyword arguments:
    credentials -- The AWSCredentials object containing access and secret keys
    region -- The region to which the data should be published
    namespace -- The namespace used for grouping of the published metrics.    
    """
    _SERVICE = "monitoring"
    _ACTION = "PutMetricData"
    _API_VERSION = "2010-08-01"
    _ALGORITHM = "AWS4-HMAC-SHA256"
    _V4_TERMINATOR = "aws4_request"
    
    def __init__(self, credentials, region):
        self.credentials = credentials
        self.region = region
        self.namespace = ""
        self.datestamp = None
        self.aws_timestamp = None
        self.payload = ""  # for HTTP GET payload is always empty
        self.querystring_builder = QuerystringBuilder()
        self.signer = Signer(credentials, region, self._SERVICE, self._ALGORITHM)
    
    def create_signed_request(self, namespace, metric_list):
        """ Creates a ready to send request with metrics from the metric list passed as parameter """
        self.namespace = namespace
        self._init_timestamps()
        canonical_querystring = self._create_canonical_querystring(metric_list)
        signature = self.signer.create_request_signature(canonical_querystring, self._get_credential_scope(),
                                            self.aws_timestamp, self.datestamp, self._get_canonical_headers(),
                                            self._get_signed_headers(), self.payload)
        canonical_querystring += '&X-Amz-Signature=' + signature
        return canonical_querystring
    
    def _init_timestamps(self):
        """ Initializes timestamp and datestamp values """ 
        self.datestamp = get_datestamp()
        self.aws_timestamp = get_aws_timestamp()
    
    def _create_canonical_querystring(self, metric_list):
        """ 
        Creates a canonical querystring as defined in the official AWS API documentation: 
        http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html 
        """
        return self.querystring_builder.build_querystring(metric_list, self._get_request_map())
    
    def _get_request_map(self):
        """
        Creates a map of request parameters and values which can be used 
        to build a canonical querystring 
        """
        canonical_map = {
            "Action": self._ACTION,
            "Namespace": self.namespace,
            "Version": self._API_VERSION,
            "X-Amz-Algorithm": self._ALGORITHM,
            "X-Amz-Credential": self.credentials.access_key + '/' + self._get_credential_scope(),
            "X-Amz-Date": self.aws_timestamp,
            "X-Amz-SignedHeaders": self._get_signed_headers()
        }
        if self.credentials.token:
            canonical_map["X-Amz-Security-Token"] = self.credentials.token
        return canonical_map
    
    def _get_credential_scope(self):
        """ Builds credential scope string used in querystring and signing """
        return self.datestamp + '/' + self.region + '/' + self._SERVICE + '/' + self._V4_TERMINATOR
                  
    def _get_canonical_headers(self):
        """ Returns a list of canonical headers separated with new line characters """ 
        return "host:" + self._get_host() + "\n"
    
    def _get_signed_headers(self):
        """ Returns comma delimited list of signed headers """
        return "host"
    
    def _get_host(self):
        """ Returns the endpoint's hostname derived from the region """
        if self.region == "localhost":
            return "localhost"
        elif self.region.startswith("cn-"):
            return "monitoring." + self.region + ".amazonaws.com.cn"
        return "monitoring." + self.region + ".amazonaws.com"
