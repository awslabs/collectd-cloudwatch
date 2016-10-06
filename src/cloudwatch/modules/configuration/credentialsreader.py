from ..awscredentials import AWSCredentials
from readerutils import ReaderUtils
from ..logger.logger import get_logger


class CredentialsReader(object):
    """
    The credentials file reader class that is responsible for reading and parsing file containing AWS credentials.
    
    The credentials file is a simple text file in format:
    aws_access_key = value
    aws_secret_key = value2
     
    Accepted configuration parameters:
    aws_access_key -- the AWS access ID used to build AWSCredentials object
    aws_secret_key -- the AWS secret key used to build AWSCredentials object
    
    Keyword arguments:
    creds_path -- the path for the credentials file to be parsed (Required)
    """

    _LOGGER = get_logger(__name__)
    _ACCESS_CONFIG_KEY = "aws_access_key"
    _SECRET_CONFIG_KEY = "aws_secret_key"

    def __init__(self, creds_path):
        self.creds_path = creds_path
        self.credentials = None
        try:
            self.reader_utils = ReaderUtils(creds_path)
            self._parse_credentials_file()
        except (CredentialsReaderException or ValueError) as e:
            raise CredentialsReaderException(e)
        except Exception as e:
            self._LOGGER.warning("Cannot read AWS credentials from file. Defaulting to use IAM Role.")

    def _parse_credentials_file(self):
        """ 
        This method retrieves values form preprocessed configuration list 
        in format ['key=value', 'key2=value2'] 
        """
        access_key = self.reader_utils.get_string(self._ACCESS_CONFIG_KEY)
        secret_key = self.reader_utils.get_string(self._SECRET_CONFIG_KEY)
        if not access_key or not secret_key:
            raise CredentialsReaderException("Access key or secret key is missing in the credentials file.")
        if access_key and secret_key:
            self.credentials = AWSCredentials(access_key, secret_key)


class CredentialsReaderException(Exception):
    pass

