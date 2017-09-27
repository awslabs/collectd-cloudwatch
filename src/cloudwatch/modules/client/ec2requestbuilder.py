from baserequestbuilder import BaseRequestBuilder


class EC2RequestBuilder(BaseRequestBuilder):
    """
    The request builder is responsible for building the DescribeTags requests using HTTP GET. 
    
    Keyword arguments:
    credentials -- The AWSCredentials object containing access and secret keys
    region -- The region to which the data should be fetched
    """
    _SERVICE = "ec2"
    _ACTION = "DescribeTags"
    _API_VERSION = "2016-11-15"
    
    def __init__(self, credentials, region):
        super(self.__class__, self).__init__(credentials, region, self._SERVICE, self._ACTION, self._API_VERSION)
    
    def create_signed_request(self, request_map):
        """ Creates a ready to send request with metrics from the metric list passed as parameter """
        self._init_timestamps()
        canonical_querystring = self._create_canonical_querystring(request_map)
        signature = self.signer.create_request_signature(canonical_querystring, self._get_credential_scope(),
                                            self.aws_timestamp, self.datestamp, self._get_canonical_headers(),
                                            self._get_signed_headers(), self.payload)
        canonical_querystring += '&X-Amz-Signature=' + signature
        return canonical_querystring
    
    def _create_canonical_querystring(self, request_map):
        """ 
        Creates a canonical querystring as defined in the official AWS API documentation: 
        http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html 
        """
        return self.querystring_builder.build_querystring_from_map(request_map, self._get_request_map())
    
    def _get_host(self):
        """ Returns the endpoint's hostname derived from the region """
        if self.region == "localhost":
            return "localhost"
        elif self.region.startswith("cn-"):
            return "ec2." + self.region + ".amazonaws.com.cn"
        return "ec2." + self.region + ".amazonaws.com"
