import hmac

from hashlib import sha256


class Signer(object):
    """
    The signer is responsible for creating v4 signatures for HTTP GET requests sent to AWS CloudWatch.
    
    Keyword arguments:
    credentials -- The AWSCredential object that contains access_key and secret_key
    region -- The AWS service region
    service -- The AWS service used in the request, for CloudWatch metrics it should always be monitoring
    algorithm -- The algorithm used to create signature and specified in the canonical query string
    """
    
    _METHOD = "GET"
    _CANONICAL_URI = "/"
    _V4_TERMINATOR = "aws4_request"
    
    def __init__(self, credentials, region, service, algorithm):
        self.credentials = credentials
        self.region = region
        self.service = service
        self.algorithm = algorithm
    
    def create_request_signature(self, canonical_querystring, credential_scope, aws_timestamp, datestamp, canonical_headers, signed_headers, payload=""):
        """ Creates a V4 request signature for the request """
        canonical_request = self._build_canonical_request(canonical_querystring, canonical_headers, signed_headers, payload)
        string_to_sign = self._build_string_to_sign(aws_timestamp, credential_scope, canonical_request)
        signing_key = self._build_signature_key(self.credentials.secret_key, datestamp, self.region, self.service)
        return self._build_signature(signing_key, string_to_sign)
    
    def _build_canonical_request(self, canonical_querystring, canonical_headers, signed_headers, payload):
        """ 
        Creates canonical request as descibed in the official documentation: 
        http://docs.aws.amazon.com/general/latest/gr/sigv4-create-canonical-request.html
        """
        return self._METHOD + '\n' + self._CANONICAL_URI + '\n' + canonical_querystring + '\n' \
               + canonical_headers + '\n' + signed_headers + '\n' + self._hash(payload)
    
    def _build_string_to_sign(self, aws_timestamp, credential_scope, canonical_request):
        """ Creates string required for deriving signature """
        return self.algorithm + "\n" + aws_timestamp + '\n' + credential_scope + '\n' + self._hash(canonical_request)

    def _hash(self, data):
        return sha256(data).hexdigest()
    
    def _sign(self, key, msg):
        return hmac.new(key, msg.encode("utf-8"), sha256).digest()
     
    def _build_signature_key(self, key, date_stamp, region_name, service_name):
        kDate = self._sign(('AWS4' + key).encode('utf-8'), date_stamp)
        kRegion = self._sign(kDate, region_name)
        kService = self._sign(kRegion, service_name)
        kSigning = self._sign(kService, self._V4_TERMINATOR)
        return kSigning

    def _build_signature(self, signing_key, string_to_sign):
        return hmac.new(signing_key, string_to_sign.encode("utf-8"), sha256).hexdigest()
