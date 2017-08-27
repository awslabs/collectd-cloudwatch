from baserequestbuilder import BaseRequestBuilder

class RequestBuilder(BaseRequestBuilder):
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
    
    def __init__(self, credentials, region, enable_high_resolution_metrics):
        super(self.__class__, self).__init__(credentials, region, self._SERVICE, self._ACTION, self._API_VERSION, enable_high_resolution_metrics)
        self.namespace = ""

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
    
    def _create_canonical_querystring(self, metric_list):
        """ 
        Creates a canonical querystring as defined in the official AWS API documentation: 
        http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html 
        """
        return self.querystring_builder.build_querystring(metric_list, self._get_namespace_request_map())
    
    def _get_namespace_request_map(self):
        """
        Creates a map of request parameters and values which can be used 
        to build a canonical querystring 
        """
        canonical_map = self._get_request_map()
        if (self.namespace):
            canonical_map["Namespace"] = self.namespace
        return canonical_map
    
    def _get_host(self):
        """ Returns the endpoint's hostname derived from the region """
        if self.region == "localhost":
            return "localhost"
        elif self.region.startswith("cn-"):
            return "monitoring." + self.region + ".amazonaws.com.cn"
        return "monitoring." + self.region + ".amazonaws.com"
