from ..logger.logger import get_logger
from readerutils import ReaderUtils


class ConfigReader(object):
    """
    The configuration reader class that is responsible for reading and parsing plugin configuration file.
    
    The plugin cofiguration file is a simple text file in format:
    key = value
    key2 = value2
     
    Accepted configuration parameters:
    credentials_path -- the path to the file with AWS access and secret keys
    region -- the region in which host operates
    host -- the host name or instance name injected to each metric as dimension
    debug -- the mode in which plugin performs verbose logging of its operations
    pass_through -- the mode in which whitelist allows use of .* on its own
    
    Keyword arguments:
    config_path -- the path for the configuration file to be parsed (Required)
    """

    _LOGGER = get_logger(__name__)
    _DEBUG_DEFAULT_VALUE = False
    _ENABLE_HIGH_DEFINITION_METRICS_DEFAULT_VALUE = False
    _PASS_THROUGH_DEFAULT_VALUE = False
    _PUSH_ASG_DEFAULT_VALUE = False
    _PUSH_CONSTANT_DEFAULT_VALUE = False
    REGION_CONFIG_KEY = "region"
    HOST_CONFIG_KEY = "host"
    CREDENTIALS_PATH_KEY = "credentials_path"
    DEBUG_CONFIG_KEY = "debug"
    PASS_THROUGH_CONFIG_KEY = "whitelist_pass_through"
    PUSH_ASG_KEY = "push_asg"
    PUSH_CONSTANT_KEY = "push_constant"
    CONSTANT_DIMENSION_KEY = "constant_dimension_value"
    PROXY_SERVER_NAME_KEY = "proxy_server_name"
    PROXY_SERVER_PORT_KEY = "proxy_server_port"
    ENABLE_HIGH_DEFINITION_METRICS = "enable_high_resolution_metrics"
    FLUSH_INTERVAL_IN_SECONDS = "flush_interval_in_seconds"

    def __init__(self, config_path):
        self.config_path = config_path
        self.credentials_path = ""
        self.region = ''
        self.host = ''
        self.pass_through = self._PASS_THROUGH_DEFAULT_VALUE
        self.debug = self._DEBUG_DEFAULT_VALUE
        self.push_asg = self._PUSH_ASG_DEFAULT_VALUE
        self.push_constant = self._PUSH_CONSTANT_DEFAULT_VALUE
        self.constant_dimension_value = ''
        self.proxy_server_name=''
        self.proxy_server_port = ''
        self.enable_high_resolution_metrics = self._ENABLE_HIGH_DEFINITION_METRICS_DEFAULT_VALUE
        self.flush_interval_in_seconds = ''
        try:
            self.reader_utils = ReaderUtils(config_path)
            self._parse_config_file()
        except Exception as e:
            self._LOGGER.warning("Cannot read plugin configuration file at: " + config_path + ". Cause: " + str(e))
            raise e
    
    def _parse_config_file(self):
        """ 
        This method retrieves values form preprocessed configuration list 
        in format ['key=value', 'key2=value2'] 
        """
        self.credentials_path = self.reader_utils.get_string(self.CREDENTIALS_PATH_KEY)
        self.host = self.reader_utils.get_string(self.HOST_CONFIG_KEY)
        self.region = self.reader_utils.get_string(self.REGION_CONFIG_KEY)
        self.proxy_server_name = self.reader_utils.get_string(self.PROXY_SERVER_NAME_KEY)
        self.proxy_server_port = self.reader_utils.get_string(self.PROXY_SERVER_PORT_KEY)
        self.enable_high_resolution_metrics = self.reader_utils.try_get_boolean(self.ENABLE_HIGH_DEFINITION_METRICS, self._ENABLE_HIGH_DEFINITION_METRICS_DEFAULT_VALUE)
        self.flush_interval_in_seconds = self.reader_utils.get_string(self.FLUSH_INTERVAL_IN_SECONDS)
        self.pass_through = self.reader_utils.try_get_boolean(self.PASS_THROUGH_CONFIG_KEY, self._PASS_THROUGH_DEFAULT_VALUE)
        self.debug = self.reader_utils.try_get_boolean(self.DEBUG_CONFIG_KEY, self._DEBUG_DEFAULT_VALUE)
        self.push_asg = self.reader_utils.try_get_boolean(self.PUSH_ASG_KEY, self._PUSH_ASG_DEFAULT_VALUE)
        self.push_constant = self.reader_utils.try_get_boolean(self.PUSH_CONSTANT_KEY, self._PUSH_CONSTANT_DEFAULT_VALUE)
        self.constant_dimension_value = self.reader_utils.get_string(self.CONSTANT_DIMENSION_KEY)
