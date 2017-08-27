import re
import os

from ..plugininfo import PLUGIN_NAME, PLUGIN_VERSION
from requestbuilder import RequestBuilder
from ..logger.logger import get_logger
from requests.adapters import HTTPAdapter
from requests.sessions import Session
from tempfile import gettempdir


class PutClient(object):
    """
    This is a simple HTTPClient wrapper which supports putMetricData operation on CloudWatch endpoints. 
    
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

    def __init__(self, config_helper, connection_timeout=_DEFAULT_CONNECTION_TIMEOUT, response_timeout=_DEFAULT_RESPONSE_TIMEOUT):
        self.request_builder = RequestBuilder(config_helper.credentials, config_helper.region, config_helper.enable_high_resolution_metrics)
        self._validate_and_set_endpoint(config_helper.endpoint)
        self.timeout = (connection_timeout, response_timeout)
        self.proxy_server_name = config_helper.proxy_server_name
        self.proxy_server_port = config_helper.proxy_server_port
        self.debug = config_helper.debug
        self.config = config_helper
        self._prepare_session()

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
            raise PutClient.InvalidEndpointException(msg)
        
    def put_metric_data(self, namespace, metric_list):
        """
        Publishes metric data to the endpoint with single namespace defined. 
        It is consumers responsibility to ensure that all metrics in the metric list 
        belong to the same namespace.
        """
        
        if not self._is_namespace_consistent(namespace, metric_list):
            raise ValueError("Metric list contains metrics with namespace different than the one passed as argument.")
        credentials = self.config.credentials
        self.request_builder.credentials = credentials
        self.request_builder.signer.credentials = credentials
        request = self.request_builder.create_signed_request(namespace, metric_list)
        try:
            self._run_request(request) 
        except Exception as e:
            self._LOGGER.warning("Could not put metric data using the following endpoint: '" + self.endpoint +"'. [Exception: " + str(e) + "]")
            self._LOGGER.warning("Request details: '" + request + "'")

    def _is_namespace_consistent(self, namespace, metric_list):
        """
        Checks if namespaces declared in MetricData objects in the metric list are consistent
        with the defined namespace.
        """
        for metric in metric_list:
            if metric.namespace is not namespace:
                return False
        return True

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
    
    def _get_custom_headers(self):
        """ Returns dictionary of HTTP headers to be attached to each request """
        return {"User-Agent": self._get_user_agent_header()}

    def _get_user_agent_header(self):
        """ Returns the plugin name and version used as User-Agent information """
        return PLUGIN_NAME + "/" + str(PLUGIN_VERSION)
    
    class InvalidEndpointException(Exception):
        pass
