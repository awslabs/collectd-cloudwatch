import re
import os

from ..plugininfo import PLUGIN_NAME, PLUGIN_VERSION
from assumerolereqbuilder import AssumeRoleReqBuilder
from ..logger.logger import get_logger
from requests.adapters import HTTPAdapter
from requests.sessions import Session
from requests import RequestException
from tempfile import gettempdir
import xml.etree.ElementTree as ET
from ..awscredentials import AWSCredentials

class StsAssumRoleClient(object):
    """
    This is a simple HTTPClient wrapper which supports assumeRole operation on sts endpoints. 
    
    Keyword arguments:
    region -- the region used for request signing.
    endpoint -- the endpoint used for publishing metric data
    credentials -- the AWSCredentials object containing access_key, secret_key or 
                IAM Role token used for request signing
    connection_timeout -- the amount of time in seconds to wait for extablishing server connection
    response_timeout -- the amount of time in seconds to wait for the server response 
    """
    
    _LOGGER = get_logger(__name__)
    _DEFAULT_CONNECTION_TIMEOUT = 1
    _DEFAULT_RESPONSE_TIMEOUT = 3
    _TOTAL_RETRIES = 1
    _LOG_FILE_MAX_SIZE = 10*1024*1024
    
    
    def __init__(self, credentials, endpoint='', region='', proxy_server_name='', proxy_server_port='', debug=False, connection_timeout=_DEFAULT_CONNECTION_TIMEOUT, response_timeout=_DEFAULT_RESPONSE_TIMEOUT):
        self.assumerole_req_builder = AssumeRoleReqBuilder(credentials, region)
        self._validate_and_set_endpoint(endpoint)
        self.timeout = (connection_timeout, response_timeout)
        self.proxy_server_name = proxy_server_name
        self.proxy_server_port = proxy_server_port
        self.debug = debug
        self._prepare_session()
    
    def get_credentials(self, arn_role, role_session_name, duration_seconds):
        """
        Requests a temporary keys by assumming give arn_role. Returns None in case of error.
        """
        request_map = {}
        request_map["RoleSessionName"] = role_session_name
        request_map["RoleArn"] = arn_role
        request_map["DurationSeconds"] = duration_seconds
        request = self.assumerole_req_builder.create_signed_request(request_map)
        
        try:
            xml_content = self._run_request(request).content
            xmldoc = ET.fromstring(xml_content)
            ns={'sts': 'https://sts.amazonaws.com/doc/2011-06-15/'}
            cred_xml = xmldoc.find('sts:AssumeRoleResult/sts:Credentials',ns)
            cred = {}
            cred["session_token"] = cred_xml.find('sts:SessionToken', ns).text.strip()
            cred["secret_access_key"] = cred_xml.find('sts:SecretAccessKey', ns).text.strip()
            cred["access_key_id"] = cred_xml.find('sts:AccessKeyId', ns).text.strip()
            cred["expiration"] = cred_xml.find('sts:Expiration', ns).text.strip()
            
            if not cred["session_token"] or not cred['secret_access_key'] or not cred["access_key_id"] or not cred["expiration"]:
                raise ValueError("Incomplete credentials retrieved.")
        except RequestException as e:
            self._LOGGER.warning("Could not assume '" + arn_role + "' using the following endpoint: '" + self.endpoint +"'. [Exception: " + str(e) + "]")
            self._LOGGER.warning("Request details: '" + request + "'")
            raise ValueError(e)
        except Exception as e:
            raise ValueError(e)
                
        return AWSCredentials(cred['access_key_id'], cred['secret_access_key'], cred["session_token"], cred["expiration"])

    def _prepare_session(self):
        self.session = Session()
        if self.proxy_server_name is not None:
            proxy_server = self.proxy_server_name
            self._LOGGER.info("Using proxy server: " + proxy_server)
            if self.proxy_server_port is not None:
                proxy_server = proxy_server + ":" + self.proxy_server_port
                self._LOGGER.info("Using proxy server port: " + self.proxy_server_port)
            proxies = {'https': proxy_server}
            self.session.proxies.update(proxies)
        else:
            self._LOGGER.info("No proxy server is in use")
        self.session.mount("http://", HTTPAdapter(max_retries=self._TOTAL_RETRIES))
        self.session.mount("https://", HTTPAdapter(max_retries=self._TOTAL_RETRIES))

    def _validate_and_set_endpoint(self, endpoint):
        pattern = re.compile("http[s]?://*/")
        if pattern.match(endpoint) or "localhost" in endpoint: 
            self.endpoint = endpoint    
        else:
            msg = "Provided endpoint '" + endpoint + "' is not a valid URL."
            self._LOGGER.error(msg)
            raise StsAssumRoleClient.InvalidEndpointException(msg)
            
    def _get_custom_headers(self):
        """ Returns dictionary of HTTP headers to be attached to each request """
        return {"User-Agent": self._get_user_agent_header()}

    def _get_user_agent_header(self):
        """ Returns the plugin name and version used as User-Agent information """
        return PLUGIN_NAME + "/" + str(PLUGIN_VERSION)
        
    def _run_request(self, request):
        """
        Executes HTTP GET request with timeout using the endpoint defined upon client creation.
        """
        if self.debug:
            file_path = gettempdir() + "/collectd_plugin_request_trace_log"
            if os.path.isfile(file_path) and os.path.getsize(file_path) > self._LOG_FILE_MAX_SIZE:
                os.remove(file_path)
            with open(file_path, "a") as logfile:
                logfile.write("curl -i -v -connect-timeout 1 -m 3 -w %{http_code}:%{http_connect}:%{content_type}:%{time_namelookup}:%{time_redirect}:%{time_pretransfer}:%{time_connect}:%{time_starttransfer}:%{time_total}:%{speed_download} -A \"collectd/1.0\" \'" + self.endpoint + "?" + request + "\'")
                logfile.write("\n\n")

        result = self.session.get(self.endpoint + "?" + request, headers=self._get_custom_headers(), timeout=self.timeout)
        result.raise_for_status()
        return result
    
    class InvalidEndpointException(Exception):
        pass
