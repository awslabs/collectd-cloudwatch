from json import loads
from requests import Session, codes
from requests.adapters import HTTPAdapter
from ..logger.logger import get_logger
from ..awscredentials import AWSCredentials


class MetadataReader(object):
    """
    The metadata reader class is responsible for retrieving configuration values from the local metadata server.
    
    Accepted configuration parameters:
    metadata_server -- the address of the local metadata server (Required)
    """
    _LOGGER = get_logger(__name__)
    _REGION_METADATA_REQUEST = "latest/meta-data/placement/availability-zone/"
    _INSTANCE_ID_METADATA_REQUEST = "latest/meta-data/instance-id/"
    _IAM_ROLE_CREDENTIAL_REQUEST = "latest/meta-data/iam/security-credentials/"
    _TOTAL_RETRIES = 3
    _CONNECT_TIMEOUT_IN_SECONDS = 0.3
    _RESPONSE_TIMEOUT_IN_SECONDS = 0.5
    _REQUEST_TIMEOUT = (_CONNECT_TIMEOUT_IN_SECONDS, _RESPONSE_TIMEOUT_IN_SECONDS)

    def __init__(self, metadata_server):
        self.metadata_server = metadata_server
        self.session = Session()
        self.session.mount("http://", HTTPAdapter(max_retries=self._TOTAL_RETRIES))
        
    def get_region(self):
        """ Get the region value from the metadata service, if the last character of region is A it is automatically trimmed """
        region = self._get_metadata(MetadataReader._REGION_METADATA_REQUEST)
        return region[:-1]

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
        result = self.session.get(self.metadata_server + request, timeout=self._REQUEST_TIMEOUT)
        if result.status_code is codes.ok:
            return str(result.text)
        else:
            self._LOGGER.error("The request: '" + str(request) + "' failed with status code: '" + str(result.status_code) + "' and message: '" + str(result.text) +"'.")
            raise MetadataRequestException("Cannot retrieve configuration from metadata service. Status code: " + str(result.status_code))


class MetadataRequestException(Exception):
    pass
