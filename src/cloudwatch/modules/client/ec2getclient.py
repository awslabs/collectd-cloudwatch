import re

from ..plugininfo import PLUGIN_NAME, PLUGIN_VERSION
from ec2requestbuilder import EC2RequestBuilder
from ..logger.logger import get_logger
from requests.adapters import HTTPAdapter
from requests.sessions import Session
import xml.etree.ElementTree as ET



class EC2GetClient(object):
    """
    This is a simple HTTPClient wrapper which supports DescribeTags operation on EC2 endpoints. 
    
    Keyword arguments:
    config_helper -- the helper that holds our configuration
    connection_timeout -- the amount of time in seconds to wait for extablishing server connection
    response_timeout -- the amount of time in seconds to wait for the server response 
    """
    
    _LOGGER = get_logger(__name__)
    _DEFAULT_CONNECTION_TIMEOUT = 1
    _DEFAULT_RESPONSE_TIMEOUT = 3
    _TOTAL_RETRIES = 1

    def __init__(self, config_helper, connection_timeout=_DEFAULT_CONNECTION_TIMEOUT, response_timeout=_DEFAULT_RESPONSE_TIMEOUT):
        self.request_builder = EC2RequestBuilder(config_helper.credentials, config_helper.region)
        self._validate_and_set_endpoint(config_helper.ec2_endpoint)
        self.timeout = (connection_timeout, response_timeout)
    
    def _validate_and_set_endpoint(self, endpoint):
        pattern = re.compile("http[s]?://*/")
        if pattern.match(endpoint) or "localhost" in endpoint: 
            self.endpoint = endpoint    
        else:
            msg = "Provided endpoint '" + endpoint + "' is not a valid URL."
            self._LOGGER.error(msg)
            raise EC2GetClient.InvalidEndpointException(msg)
        
    def get_autoscaling_group(self, instanceId):
        """
        Fetches the autoscaling group name from EC2. Defatuls to NONE if an error occours
        """
        request_map = {}
        request_map["Filter.1.Name"] = "key"
        request_map["Filter.1.Value.1"] = "aws:autoscaling:groupName"
        request_map["Filter.2.Name"] = "resource-id"
        request_map["Filter.2.Value.1"] = instanceId
        request = self.request_builder.create_signed_request(request_map)
        try:
            xml_content = self._run_request(request).content
            xmldoc = ET.fromstring(xml_content)
            ns={'ec2': 'http://ec2.amazonaws.com/doc/2016-11-15/'}
            return xmldoc.findall('ec2:tagSet/ec2:item[0]/ec2:value',ns)[0].text
        except Exception as e:
            self._LOGGER.warning("Could not get the autoscaling group name using the following endpoint: '" + self.endpoint +"'. [Exception: " + str(e) + "]")
            self._LOGGER.warning("Request details: '" + request + "'")
            return "NONE"

    def _run_request(self, request):
        """
        Executes HTTP GET request with timeout using the endpoint defined upon client creation.
        """
        session = Session()
        session.mount("http://", HTTPAdapter(max_retries=self._TOTAL_RETRIES))
        session.mount("https://", HTTPAdapter(max_retries=self._TOTAL_RETRIES))
        result = session.get(self.endpoint + "?" + request, headers=self._get_custom_headers(), timeout=self.timeout)
        result.raise_for_status()
        return result
    
    def _get_custom_headers(self):
        """ Returns dictionary of HTTP headers to be attached to each request """
        return {"User-Agent": self._get_user_agent_header(), "Accept": "application/json", "content-type" : "application/json"}

    def _get_user_agent_header(self):
        """ Returns the plugin name and version used as User-Agent information """
        return PLUGIN_NAME + "/" + str(PLUGIN_VERSION)
    
    class InvalidEndpointException(Exception):
        pass
