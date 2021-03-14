from json import loads
from requests import Session, codes
from requests.adapters import HTTPAdapter
from cloudwatch.modules.logger.logger import get_logger
from cloudwatch.modules.awscredentials import AWSCredentials




class MetadataReader(object):
    """
    The metadata reader class is responsible for retrieving configuration values from the local metadata server.
    
    Accepted configuration parameters:
    metadata_server -- the address of the local metadata server (Required)
    """
    _LOGGER = get_logger(__name__)
    _IDENTITY_DOCUMENT_REQUEST = "latest/dynamic/instance-identity/document"
    _INSTANCE_ID_METADATA_REQUEST = "latest/meta-data/instance-id/"
    _IAM_ROLE_CREDENTIAL_REQUEST = "latest/meta-data/iam/security-credentials/"
    _TOTAL_RETRIES = 3
    _CONNECT_TIMEOUT_IN_SECONDS = 0.3
    _RESPONSE_TIMEOUT_IN_SECONDS = 0.5
    _REQUEST_TIMEOUT = (_CONNECT_TIMEOUT_IN_SECONDS, _RESPONSE_TIMEOUT_IN_SECONDS)
    _TOKEN_REQUEST = "latest/api/token"
    _TOKEN_TTL_SECONDS = 21600 # 6 hours
    _X_AWS_EC_METADATA_TOKEN = 'X-aws-ec2-metadata-token'
    _TTL_SECONDS = "X-aws-ec2-metadata-token-ttl-seconds"

    def __init__(self, metadata_server):
        self.metadata_server = metadata_server
        self.session = Session()
        self.session.mount("http://", HTTPAdapter(max_retries=self._TOTAL_RETRIES))
        self.token = ""

    def get_region(self):
        """ Get the region value from the metadata service """
        document = self._get_metadata(MetadataReader._IDENTITY_DOCUMENT_REQUEST)
        return loads(document)['region']

    def get_instance_id(self):
        """ Get the instance id value from the metadata service """
        return self._get_metadata(MetadataReader._INSTANCE_ID_METADATA_REQUEST)

    def get_iam_role_name(self):
        """ Get the name of IAM Role applied to the EC2 instance """
        return self._get_metadata(self._IAM_ROLE_CREDENTIAL_REQUEST)
    
    def get_iam_role_credentials(self, role_name):
        """ Get the IAMRoleCredentials object with values from IAM metadata """
        try:
            iam_data = loads(self._get_metadata(self._IAM_ROLE_CREDENTIAL_REQUEST + role_name))
            if iam_data['AccessKeyId'] and iam_data['SecretAccessKey'] and iam_data['Token']:
                return AWSCredentials(iam_data['AccessKeyId'], iam_data['SecretAccessKey'], iam_data['Token'])
            else:
                raise ValueError("Incomplete credentials retrieved.")
        except Exception as e:
            self._LOGGER.error("Retrieved IAM data is invalid. Cause: " + str(e))
            raise ValueError(e)
        
    def _get_metadata(self, request): 
        """
        This method retrieves values from metadata service.
        
        request -- The request part after the metadata service address, for example if full request is:
                   'http://169.254.169.254/latest/meta-data/placement/availability-zone/' 
                   then the request part is 'latest/meta-data/placement/availability-zone/'.
        """
        result = self._v2_call(request)
        if result and result.status_code is codes.ok:
            return str(result.text)

        result = self._v1_call(request)
        if result.status_code is codes.ok:
            return str(result.text)
        else:
            self._LOGGER.error("The request: '" + str(request) + "' failed with status code: '" + str(result.status_code) + "' and message: '" + str(result.text) + "'.")
            raise MetadataRequestException("Cannot retrieve configuration from metadata service. Status code: " + str(result.status_code))

    def _v1_call(self, request):
        self._LOGGER.info("[debug] Fallback to IMDSV1")
        result = self.session.get(self.metadata_server + request, timeout=self._REQUEST_TIMEOUT)
        return result

    def _v2_call(self, request):
        try:
            if not self.token:
                self.token = self._get_metadata_token()
            headers = {self._X_AWS_EC_METADATA_TOKEN:self.token}
            result = self.session.get(self.metadata_server + request, timeout=self._REQUEST_TIMEOUT, headers=headers)
            # In case that token expired, we need to try v2 again.
            if result.status_code == codes.unauthorized:
                self._LOGGER.info("[debug] unauthorized token, try IMDSV2 again.")
                self.token = self._get_metadata_token()
                headers = {self._X_AWS_EC_METADATA_TOKEN:self.token}
                result = self.session.get(self.metadata_server + request, timeout=self._REQUEST_TIMEOUT, headers=headers)
            return result
        except Exception as e:
            return False

    def _get_metadata_token(self):
        """
        This method retrieves token from metadata service.
        """
        try:
            headers = {self._TTL_SECONDS:str(self._TOKEN_TTL_SECONDS)}
            result = self.session.put(self.metadata_server + self._TOKEN_REQUEST, timeout=self._REQUEST_TIMEOUT, headers=headers)
        except Exception as e:
            raise MetadataRequestException("%s cannot access metadata service. url:%s, Cause: %s " %(self._get_metadata_token.__name__, self._TOKEN_REQUEST, str(e)) )
        if result.status_code is not codes.ok:
            raise MetadataRequestException("%s cannot retrieve configuration from metadata service. url:%s, Status code: %s"  %(self._get_metadata_token.__name__, self._TOKEN_REQUEST, str(result.status_code)))
        return str(result.text)

class MetadataRequestException(Exception):
    pass
