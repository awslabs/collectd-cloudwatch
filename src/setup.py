#!/usr/bin/env python
"""
The installation script provides the following key functions:
1. Installation of dependencies required for the plugin.
2. Download and extraction of plugin source code into a predefined location /opt/collectd-plugins/
3. Plugin configuration using EC2 metadata as defaults if possible.
4. Configuration of Collectd in order to use this plugin.

Depending on the version of collectd installed on the host we provide the following options:
1. version >= 5.5.0 - by default we will supply a configuration and whitelist with percentage host metrics enabled.
2. version >= 5.0.0 - we will offer option to inject our plugin into the existing configuration (no metrics are whitelisted).
3. any other version of collectd is not supported.
"""

import os
import platform
import re
import shlex
import shutil
import time
import errno
import argparse
import logging
from collections import namedtuple
from distutils.version import LooseVersion
from glob import glob
from os import path, makedirs, chdir
from subprocess import check_output, CalledProcessError, Popen, PIPE
from tempfile import gettempdir

ROOT_UID = 0
TEMP_DIRECTORY = gettempdir() + "/collectd-cloudwatch-plugin/"
TIMESTAMP_FORMAT = "%Y-%m-%d_%H_%M"
TAR_FILE = "awslabs-collectd-cloudwatch.tar.gz"
DOWNLOAD_PLUGIN_DIR = "awslabs-collectd-cloudwatch*"
DEFAULT_PLUGIN_CONFIGURATION_DIR = "/opt/collectd-plugins/cloudwatch/config"
NEW_PLUGIN_FILES = DOWNLOAD_PLUGIN_DIR + "/src/*"
RECOMMENDED_COLLECTD_CONFIGURATION = DOWNLOAD_PLUGIN_DIR + "/resources/collectd.conf"
RECOMMENDED_WHITELIST = DOWNLOAD_PLUGIN_DIR + "/resources/whitelist.conf"
PLUGIN_INCLUDE_CONFIGURATION = DOWNLOAD_PLUGIN_DIR + "/resources/collectd-cloudwatch.conf"
PLUGIN_CONFIGURATION_INCLUDE_LINE = 'Include "/etc/collectd-cloudwatch.conf"\r\n'
APT_INSTALL_COMMAND = "apt-get install -y "
YUM_INSTALL_COMMAND = "yum install -y "
SYSTEM_DEPENDENCIES = ["python-pip", "python-setuptools"]
PIP_INSTALLATION_FLAGS = " install --quiet --upgrade --force-reinstall "
EASY_INSTALL_COMMAND = "easy_install -U --quiet "
PYTHON_DEPENDENCIES = ["requests"]
FIND_COMMAND = "which {} 2> /dev/null"
COLLECTD_HELP_ARGS = "-help"
CONFIG_FILE_REGEX = re.compile("\sConfig file\s*(.*)\s")
VERSION_REGEX = re.compile("\scollectd ([\d*].*[\d*]).*\s")
DISTRO_NAME_REGEX = re.compile("(?<!...)NAME=\"?([\w\s]*)\"?\s?")
CLOUD_WATCH_COLLECTD_DETECTION_REGEX = re.compile('^Import [\'\"]cloudwatch_writer[\"\']$|collectd-cloudwatch\.conf', re.MULTILINE | re.IGNORECASE)
COLLECTD_CONFIG_INCLUDE_REGEX = re.compile("^Include [\'\"](.*?\.conf)[\'\"]", re.MULTILINE | re.IGNORECASE)
COLLECTD_PYTHON_PLUGIN_CONFIGURATION_REGEX = re.compile("^LoadPlugin python$|^<LoadPlugin python>$", re.MULTILINE | re.IGNORECASE)

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

DISTRIBUTION_TO_INSTALLER = {
    "Ubuntu": APT_INSTALL_COMMAND,
    "Red Hat Enterprise Linux Server": YUM_INSTALL_COMMAND,
    "Amazon Linux AMI": YUM_INSTALL_COMMAND,
    "CentOS Linux": YUM_INSTALL_COMMAND,
}


class InstallationFailedException(Exception):
    pass


class CollectdInfo(object):
    MIN_SUPPORTED_VERSION = "5.0.0"
    MIN_RECOMMENDED_VERSION = "5.5.0"
    PLUGINS_DIR = "/opt/collectd-plugins"
    DEFAULT_COMPILE_PATH = "/opt/collectd/sbin/collectd"

    def __init__(self, exec_path, config_path, version):
        self.exec_path = exec_path
        self.config_path = config_path
        self.version = version

    def is_supported_version(self):
        return self._is_newer_than(self.MIN_SUPPORTED_VERSION)

    def is_recommended_version(self):
        return self._is_newer_than(self.MIN_RECOMMENDED_VERSION)

    def _is_newer_than(self, target):
        return LooseVersion(target) <= LooseVersion(self.version)


class Color(object):
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    END = '\033[0m'

    @classmethod
    def red(cls, string):
        return cls.RED + string + cls.END

    @classmethod
    def green(cls, string):
        return cls.GREEN + string + cls.END

    @classmethod
    def yellow(cls, string):
        return cls.YELLOW + string + cls.END

    @classmethod
    def cyan(cls, string):
        return cls.CYAN + string + cls.END


def get_collectd_info():
    exec_path = _get_collectd_exec()
    output = check_output([exec_path, COLLECTD_HELP_ARGS])
    version = VERSION_REGEX.search(output).group(1)
    config_path = CONFIG_FILE_REGEX.search(output).group(1)
    return CollectdInfo(exec_path, config_path, version)


def _get_collectd_exec():
    try:
        return get_path_to_executable("collectd")
    except CalledProcessError:
        if path.exists(CollectdInfo.DEFAULT_COMPILE_PATH):
            return CollectdInfo.DEFAULT_COMPILE_PATH
    raise InstallationFailedException("Cannot detect collectd.")


def get_path_to_executable(command):
    return check_output(FIND_COMMAND.format(command), shell=True).strip()


class Command(object):
    SUCCESS = 0
    OK = "... " + Color.green("OK")
    NOT_OK = "... " + Color.red("NOT OK")
    INVALID_COMMAND_ERROR_MSG = Color.red("ERROR: Could not execute the following command: {command}.")
    ERROR_MSG = Color.red("Installation cancelled due to an error.\nExecuted command: '{command}'."
                          "\nError output: '{error_output}'.")

    def __init__(self, command, message, exit_on_failure=False, shell=False):
        self.message = message
        self.stdout = ""
        self.stderr = ""
        self._command = command
        self._process = None
        self._shell = shell
        self._exit_on_failure = exit_on_failure

    @property
    def was_successful(self):
        return self._process and self._process.returncode is self.SUCCESS

    def run(self):
        print self.message,  # comma stops print from adding line break at the end
        try:
            self._process = self._get_process()
            self._capture_outputs()
        except OSError:
            self.stderr = self.INVALID_COMMAND_ERROR_MSG.format(command=self._command)
        finally:
            self._output_command_status()
        if not self.was_successful and self._exit_on_failure:
            raise InstallationFailedException(self.ERROR_MSG.format(command=self._command, error_output=self.stderr))

    def _get_process(self):
        command = self._command
        if not self._shell:
            command = shlex.split(self._command)
        return Popen(command, shell=self._shell, stdout=PIPE, stderr=PIPE)

    def _capture_outputs(self):
        stdout, stderr = self._process.communicate()
        self.stdout = str(stdout).strip()
        self.stderr = str(stderr).strip()

    def _output_command_status(self):
        result = self.NOT_OK
        if self.was_successful:
            result = self.OK
        print result


class MetadataReader(object):
    """
    The metadata reader class is responsible for retrieving configuration values from the local metadata server.
    """
    _METADATA_SERVICE_ADDRESS = 'http://169.254.169.254/'
    _REGION_METADATA_REQUEST = "latest/meta-data/placement/availability-zone/"
    _INSTANCE_ID_METADATA_REQUEST = "latest/meta-data/instance-id/"
    _IAM_ROLE_CREDENTIAL_REQUEST = "latest/meta-data/iam/security-credentials/"
    _MAX_RETRIES = 1
    _CONNECT_TIMEOUT_IN_SECONDS = 0.3
    _RESPONSE_TIMEOUT_IN_SECONDS = 0.5
    _REQUEST_TIMEOUT = (_CONNECT_TIMEOUT_IN_SECONDS, _RESPONSE_TIMEOUT_IN_SECONDS)

    def __init__(self):
        self.metadata_server = self._METADATA_SERVICE_ADDRESS

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

    def _get_metadata(self, request):
        """
        This method retrieves values from metadata service.

        request -- The request part after the metadata service address, for example if full request is:
                   'http://169.254.169.254/latest/meta-data/placement/availability-zone/'
                   then the request part is 'latest/meta-data/placement/availability-zone/'.
        """
        from requests import Session, codes
        from requests.adapters import HTTPAdapter
        try:
            session = Session()
            session.mount("http://", HTTPAdapter(max_retries=self._MAX_RETRIES))
            result = session.get(self.metadata_server + request, timeout=self._REQUEST_TIMEOUT)
        except Exception as e:
            raise MetadataRequestException("Cannot access metadata service. Cause: " + str(e))
        if result.status_code is not codes.ok:
            raise MetadataRequestException("Cannot retrieve configuration from metadata service. Status code: " + str(result.status_code))
        return str(result.text)


class MetadataRequestException(Exception):
    pass


def install_python_packages(packages):
    try:
        Command(detect_pip() + PIP_INSTALLATION_FLAGS + " ".join(packages), "Installing python dependencies", exit_on_failure=True).run()
    except CalledProcessError:
        Command(EASY_INSTALL_COMMAND + " ".join(packages), "Installing python dependencies", exit_on_failure=True).run()


def detect_pip():
    try:
        return get_path_to_executable("pip")
    except CalledProcessError:
        return get_path_to_executable("python-pip")


def install_packages(packages):
    command = DISTRIBUTION_TO_INSTALLER[detect_linux_distribution()] + " ".join(packages)
    Command(command, "Installing dependencies").run()


def detect_linux_distribution():
    search_string = ""
    for release_file in glob("/etc/*-release"):
        with open(release_file) as fd:
            search_string += fd.read()
    return DISTRO_NAME_REGEX.search(search_string).group(1).strip()


def make_dirs(directory):
    try:
        makedirs(directory)
    except OSError as e:
        if e.errno is not errno.EEXIST:
            raise InstallationFailedException("Could not create directory: {}. Cause: {}".format(directory, str(e)))


class PluginConfig(object):
    CREDENTIALS_PATH_KEY = "credentials_path"
    REGION_KEY = "region"
    HOST_KEY = "host"
    PROXY_SERVER_NAME = "proxy_server_name"
    PROXY_SERVER_PORT = "proxy_server_port"
    PASS_THROUGH_KEY = "whitelist_pass_through"
    PUSH_ASG_KEY = "push_asg"
    PUSH_CONSTANT_KEY = "push_constant"
    CONSTANT_DIMENSION_VALUE_KEY = "constant_dimension_value"
    DEBUG_KEY = "debug"
    ACCESS_KEY = "aws_access_key"
    SECRET_KEY = "aws_secret_key"

    def __init__(self, credentials_path=None, access_key=None, secret_key=None, region=None, host=None, proxy_server_name=None, proxy_server_port=None, push_asg=None, push_constant=None, constant_dimension_value=None):
        self.credentials_path = credentials_path
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.host = host
        self.use_recommended_collectd_config = False
        self.only_add_plugin = False
        self.debug = False
        self.pass_through = False
        self.credentials_file_exist = False
        self.proxy_server_name = proxy_server_name
        self.proxy_server_port = proxy_server_port
        self.push_asg = push_asg
        self.push_constant = push_constant
        self.constant_dimension_value = constant_dimension_value


class InteractiveConfigurator(object):
    DEFAULT_PROMPT = "Enter choice [" + Color.green("{default}") + "]: "

    def __init__(self, plugin_config, metadata_reader, collectd_info, non_interactive, region, host,
                 proxy_name, proxy_port, access_key, secret_key, creds_path, installation_method,push_asg,
                 push_constant, dimension_value, debug):
        self.config = plugin_config
        self.metadata_reader = metadata_reader
        self.collectd_info = collectd_info
        self.non_interactive = non_interactive
        self.region = region
        self.host = host
        self.proxy_name = proxy_name
        self.proxy_port = proxy_port
        self.access_key = access_key
        self.secret_key = secret_key
        self.creds_path = creds_path
        self.installation_method = installation_method
        self.push_asg = push_asg
        self.push_constant = push_constant
        self.dimension_value = dimension_value
        self.debug = debug

    def run(self):
        if self.non_interactive:
            self._configure_region_non_interactive()
            self._configure_hostname_non_interactive()
            self._configure_credentials_non_interactive()
            self._configure_proxy_server_name_non_interactive()
            self._configure_proxy_server_port_non_interactive()
            self._configure_push_asg_non_interactive()
            self._configure_push_constant_non_interactive()
            self._configure_plugin_installation_method_non_interactive()
            if self.debug: self._debug()
        else:
            self._configure_region()
            self._configure_hostname()
            self._configure_credentials()
            self._configure_proxy_server_name()
            self._configure_proxy_server_port()
            self._configure_push_asg()
            self._configure_push_constant()
            self._configure_plugin_installation_method()
        
    def _configure_push_asg_non_interactive(self):
        if self.push_asg:
            self.config.push_asg = True
        else:
            self.config.push_asg = False

    def _configure_push_asg(self):
        self.config.push_asg = False
        choice = Prompt("\nInclude the Auto-Scaling Group name as a metric dimension:", options=["No", "Yes"], default="1").run()
        if choice == "2":
            self.config.push_asg = True
            
    def _get_constant_dimension_value(self):
        return Prompt(message="Enter FixedDimension value [" + Color.green("ALL") + "]: ", default="ALL").run()

    def _configure_push_constant_non_interactive(self):
        if self.push_constant and self.dimension_value:
            self.config.push_constant = True
            self.config.constant_dimension_value = self.dimension_value
        else:
            self.config.push_constant = False
            self.config.constant_dimension_value = "ALL"

    def _configure_push_constant(self):
        self.config.push_constant = False
        self.config.constant_dimension_value = "ALL"
        choice = Prompt("\nInclude the FixedDimension as a metric dimension:", options=["No", "Yes"], default="1").run()
        if choice == "2":
            self.config.push_constant = True
            self.config.constant_dimension_value = self._get_constant_dimension_value()

    def _configure_region_non_interactive(self):
        if self.region:
            self.config.region = self.region
        else:
            self._configure_region()

    def _configure_region(self):
        try:
            region = self.metadata_reader.get_region()
            if self.non_interactive:
                self.config.region = region
            else:
                choice = Prompt("\nChoose AWS region for published metrics:", ["Automatic [" + region + "]", "Custom"],
                                default="1").run()
                if choice == "2":
                    self.config.region = self._get_region()
        except MetadataRequestException as e:
            print(Color.yellow("\nAWS region could not be automatically detected. Cause:" + str(e)))
            self.config.region = self._get_region()

    def _get_region(self):
        return Prompt("Enter one of the available regions from: " +
                      Color.cyan("http://docs.aws.amazon.com/general/latest/gr/rande.html#cw_region"),
                      message="Enter region: ").run()

    def _configure_hostname_non_interactive(self):
        if self.host:
            self.config.host = self.host
        else:
            self._configure_hostname()

    def _configure_hostname(self):
        try:
            instance_id = self.metadata_reader.get_instance_id()
            if self.non_interactive:
                self.config.host = instance_id
            else:
                choice = Prompt("\nChoose hostname for published metrics:", ["EC2 instance id [" + instance_id + "]", "Custom"],
                                default="1").run()
                if choice == "2":
                    self.config.host = self._get_hostname()
        except MetadataRequestException:
            print(Color.yellow("\nEC2 instance id could not be automatically detected."))
            self.config.host = self._get_hostname()

    def _get_hostname(self):
        hostname = platform.node()
        return Prompt(message="Enter hostname [" + Color.green(hostname) + "]: ", default=hostname).run()

    def _configure_proxy_server_name_non_interactive(self):
        if self.proxy_name:
            self.config.proxy_server_name = self.proxy_name
        else:
            self.config.proxy_server_name = None

    def _configure_proxy_server_name(self):
        proxy_server_name = None
        choice = Prompt("\nEnter proxy server name:", options=[None, "Custom"],default="1").run()
        if choice == "2":
            self.config.proxy_server_name = self._get_proxy_server_name()

    def _get_proxy_server_name(self):
        proxy_server_name = None
        return Prompt("\nEnter proxy server name (e.g. http[s]://hostname):", default=None).run()

    def _configure_proxy_server_port_non_interactive(self):
        if self.proxy_port:
            self.config.proxy_server_port = self.proxy_port
        else:
            self.config.proxy_server_port = None

    def _configure_proxy_server_port(self):
        proxy_server_port = None
        choice = Prompt("\nEnter proxy server port:", options=[None, "Custom"],default="1").run()
        if choice == "2":
            self.config.proxy_server_port = self._get_proxy_server_port()

    def _get_proxy_server_port(self):
        proxy_server_port = None
        return Prompt("\nEnter proxy server port (e.g. 8080):", default=None).run()

    def _configure_credentials_non_interactive(self):
        if self.access_key and self.secret_key:
            self.config.credentials_path = self._get_credentials_path()
        self.config.credentials_file_exist = path.exists(str(self.config.credentials_path))
        if not self.config.credentials_file_exist:
            self.config.access_key = self.access_key
            self.config.secret_key = self.secret_key

    def _configure_credentials(self):
        if self._is_iam_user_required():
            self.config.credentials_path = self._get_credentials_path()
            self.config.credentials_file_exist = path.exists(self.config.credentials_path)
            if not self.config.credentials_file_exist:
                self.config.access_key = Prompt(message="Enter access key: ").run()
                self.config.secret_key = Prompt(message="Enter secret key: ").run()

    def _is_iam_user_required(self):
        try:
            iam_role = self.metadata_reader.get_iam_role_name()
            if not self.non_interactive:
                answer = Prompt("\nChoose authentication method:", ["IAM Role [" + iam_role + "]", "IAM User"], default="1").run()
                return answer == "2"
        except MetadataRequestException:
            print(Color.yellow("\nIAM Role could not be automatically detected."))
            return True

    def _get_credentials_path(self):
        recommended_path = path.expanduser('~') + '/.aws/credentials'
        creds_path = ""
        if not self.non_interactive:
            while not path.isabs(creds_path):
                creds_path = Prompt(
                    message="Enter absolute path to AWS credentials file [" + Color.green(recommended_path) + "]: ",
                    default=recommended_path).run()
        else:
            if self.creds_path:
                if path.isabs(self.creds_path):
                    creds_path = self.creds_path
            else:
                creds_path = recommended_path
        make_dirs(path.dirname(creds_path))
        return creds_path

    def _configure_plugin_installation_method(self):
        options = ["Do not modify existing collectd configuration"]
        default = "1"
        if self.collectd_info.is_supported_version():
            options.append("Add plugin to the existing configuration")
            default = "2"
        if self.collectd_info.is_recommended_version():
            options.append("Use CloudWatch recommended configuration (4 metrics)")
            default = "3"
        answer = Prompt("\nChoose how to install CloudWatch plugin in collectd:", options, default=default).run()
        if answer == "2":
            self.config.only_add_plugin = True
        elif answer == "3":
            self.config.use_recommended_collectd_config = True

    def _configure_plugin_installation_method_non_interactive(self):
        # recommended|add|not_modify
        if not self.installation_method:
            pass
        else:
            if self.installation_method == 'not_modify':
                pass
            if self.installation_method == 'add':
                self.config.only_add_plugin = True
            if self.installation_method == 'recommended':
                self.config.use_recommended_collectd_config = True

    def _debug(self):
        logger.info('-=**********DEBUG**********=-')
        logger.info('PUSH ASG: {}'.format(self.config.push_asg))
        logger.info('PUSH CONSTANT: {}'.format(self.config.push_constant))
        logger.info('CONSTANT DIMENSION VALUE: {}'.format(self.config.constant_dimension_value))
        logger.info('CREDENTIALS PATH: {}'.format(self.config.credentials_path))
        logger.info('SECRET KEY: {}'.format(self.config.secret_key))
        logger.info('ACCESS KEY: {}'.format(self.config.access_key))
        logger.info('HOST: {}'.format(self.config.host))
        logger.info('PROXY NAME: {}'.format(self.config.proxy_server_name))
        logger.info('PROXY PORT: {}'.format(self.config.proxy_server_port))
        logger.info('CREDENTIALS PATH: {}'.format(self.config.credentials_path))
        logger.info('METHOD ONLY ADD PLUGIN: {}'.format(self.config.only_add_plugin))
        logger.info('USE RECOMMENDED CONFIG: {}'.format(self.config.use_recommended_collectd_config))
        logger.info('REGION: {}'.format(self.config.region))

class Prompt(object):
    _DEFAULT_PROMPT = "Enter choice [" + Color.green("{}") + "]: "

    def __init__(self, title=None, options=None, message=_DEFAULT_PROMPT, default=None, allowed_values=None):
        self.title = title
        self.options = options
        self.message = message
        self.default = default
        self.allowed_values = allowed_values
        self._prepare_prompt()

    def _prepare_prompt(self):
        if self.message == self._DEFAULT_PROMPT:
            self.message = self.message.format(self.default)

    def run(self):
        if self.title:
            print self.title
        if self.options:
            for index, option in enumerate(self.options, start=1):
                print "  {}. {}".format(index, option)
        return self._get_answer()

    def _get_answer(self):
        value = raw_input(self.message).strip()
        while self._is_value_invalid(value):
            value = raw_input(self.message).strip()
        return value or str(self.default)

    def _is_value_invalid(self, value):
        return (not value and not self.default) \
               or (value and self.allowed_values and value not in self.allowed_values) \
               or (value and self.options and value not in [str(x) for x in range(1, len(self.options)+1)])


class PluginConfigWriter(object):
    TEMPLATE = """# The path to the AWS credentials file. This value has to be provided if plugin is used outside of EC2 instances
$credentials_path$

# The target region which will be used to publish metric data
# For list of valid regions visit: http://docs.aws.amazon.com/general/latest/gr/rande.html#cw_region
$region$

# The host parameter can be used to override instance-id or host information published with every metric
$host$

# The pass through option allows unsafe regular expressions such as '.*' or '.+'.
# WARNING: ENABLING THIS OPTION MAY LEAD TO PUBLISHING A LARGE NUMBER OF METRICS
#   SEE https://aws.amazon.com/cloudwatch/pricing/ TO UNDERSTAND HOW TO ESTIMATE YOUR BILL.
$whitelist_pass_through$

# The debug parameter enables verbose logging of published metrics
$debug$

# Wheter or not to push the ASG as part of the dimension.
# WARNING: ENABLING THIS WILL LEAD TO CREATING A LARGE NUMBER OF METRICS.
$push_asg$

# Whether or not to push the constant value to CWM as a metric
$push_constant$

# Constant dimension value to add to CWL
$constant_dimension_value$

# This parameter contains proxy server name to connect aws, if needed. Foramt is http[s]://PROXYHOST
$proxy_server_name$

# This parameter contains proxy server port to connect aws, if needed.
$proxy_server_port$
"""
    DEFAULT_PLUGIN_CONFIG_FILE = path.join(DEFAULT_PLUGIN_CONFIGURATION_DIR, "plugin.conf")

    def __init__(self, plugin_config):
        self.plugin_config = plugin_config

    def write(self):
        self._write_plugin_configuration_file()
        if self.plugin_config.credentials_path and not self.plugin_config.credentials_file_exist:
            self._write_credentials_file()

    def _write_plugin_configuration_file(self):
        try:
            with open(self.DEFAULT_PLUGIN_CONFIG_FILE, "w") as config_file:
                config_file.write(self._prepare_config())
                print(Color.green("Plugin configuration written successfully."))
        except IOError as e:
            raise InstallationFailedException("Could not write plugin configuration file. Cause: {}".format(str(e)))

    def _write_credentials_file(self):
        try:
            with open(self.plugin_config.credentials_path, 'w') as credentials_file:
                credentials_file.write('{} = "{}"\n'.format(self.plugin_config.ACCESS_KEY, self.plugin_config.access_key))
                credentials_file.write('{} = "{}"\n'.format(self.plugin_config.SECRET_KEY, self.plugin_config.secret_key))
                print(Color.green("Credentials configuration written successfully."))
        except IOError as e:
            raise InstallationFailedException("Could not write credentials to file. Cause: {}".format(str(e)))

    def _prepare_config(self):
        config = self.TEMPLATE
        config = self._replace_with_value(config, self.plugin_config.CREDENTIALS_PATH_KEY, self.plugin_config.credentials_path)
        config = self._replace_with_value(config, self.plugin_config.REGION_KEY, self.plugin_config.region)
        config = self._replace_with_value(config, self.plugin_config.HOST_KEY, self.plugin_config.host)
        config = self._replace_with_value(config, self.plugin_config.PASS_THROUGH_KEY, self.plugin_config.pass_through)
        config = self._replace_with_value(config, self.plugin_config.DEBUG_KEY, self.plugin_config.debug)
        config = self._replace_with_value(config, self.plugin_config.PROXY_SERVER_NAME, self.plugin_config.proxy_server_name)
        config = self._replace_with_value(config, self.plugin_config.PROXY_SERVER_PORT, self.plugin_config.proxy_server_port)
        config = self._replace_with_value(config, self.plugin_config.PUSH_ASG_KEY, self.plugin_config.push_asg)
        config = self._replace_with_value(config, self.plugin_config.PUSH_CONSTANT_KEY, self.plugin_config.push_constant)
        config = self._replace_with_value(config, self.plugin_config.CONSTANT_DIMENSION_VALUE_KEY, self.plugin_config.constant_dimension_value)
        return config

    def _replace_with_value(self, string, key, value):
        template_key = "${}$".format(key)
        if value is None:
            return string.replace(template_key, '# {} = '.format(key))
        return string.replace(template_key, '{} = "{}"'.format(key, value))


def main():
    CMD = namedtuple("cmd", "cmd, msg")
    COLLECTD_INFO = get_collectd_info()
    STOP_COLLECTD_CMD = CMD("pkill collectd", "Stopping collectd process")
    START_COLLECTD_CMD = CMD(COLLECTD_INFO.exec_path, "Starting collectd process")
    DOWNLOAD_PLUGIN_CMD = CMD("curl -sL https://github.com/awslabs/collectd-cloudwatch/tarball/master > " + TAR_FILE, "Downloading plugin")
    UNTAR_PLUGIN_CMD = CMD("tar zxf " + TAR_FILE, "Extracting plugin")
    COPY_CMD = "\cp -rf {source} {target}"
    COPY_PLUGIN_CMD = CMD(COPY_CMD.format(source=NEW_PLUGIN_FILES, target=CollectdInfo.PLUGINS_DIR), "Moving to collectd plugins directory")
    COPY_PLUGIN_INCLUDE_FILE_CMD = CMD(COPY_CMD.format(source=PLUGIN_INCLUDE_CONFIGURATION, target="/etc/"), "Copying CloudWatch plugin include file")
    COPY_RECOMMENDED_COLLECTD_CONFIG_CMD = CMD(COPY_CMD.format(source=RECOMMENDED_COLLECTD_CONFIGURATION, target=COLLECTD_INFO.config_path), "Replacing collectd configuration")
    BACKUP_COLLECTD_CONFIG_CMD = CMD(COPY_CMD.format(source=COLLECTD_INFO.config_path, target=COLLECTD_INFO.config_path + "." + time.strftime(TIMESTAMP_FORMAT)),
                                 "Creating backup of the original configuration")
    REPLACE_WHITELIST_CMD = CMD(COPY_CMD.format(source=RECOMMENDED_WHITELIST, target=DEFAULT_PLUGIN_CONFIGURATION_DIR), "Replacing whitelist configuration")

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Script for custom installation process for collectd AWS CloudWatch plugin'
    )
    parser.add_argument(
        '-i', '--non_interactive', required=False,
        help='Non interactive mode',
        default=False, action='store_true'
    )
    parser.add_argument(
        '-H', '--host_name', required=False,
        help='Manual override for EC2 Instance ID and Host information propagated by collectd',
        metavar='HOST_NAME', default=None
    )
    parser.add_argument(
        '-r', '--region', required=False,
        help='Manual override for region used to publish metrics',
        metavar='REGION', default=None
    )
    parser.add_argument(
        '-n', '--proxy_name', required=False,
        help='Proxy server name',
        metavar='NAME', default=None
    )
    parser.add_argument(
        '-p', '--proxy_port', required=False,
        help='Proxy server port',
        metavar='PORT', default=None
    )
    parser.add_argument(
        '-a', '--access_key', required=False,
        help='AWS IAM user access key',
        metavar='ACCESS_KEY', default=None
    )
    parser.add_argument(
        '-s', '--secret_key', required=False,
        help='AWS IAM user secret key',
        metavar='SECRET_KEY', default=None
    )
    parser.add_argument(
        '-P', '--creds_path', required=False,
        help='Absolute path to AWS credentials file',
        metavar='CREDENTIALS_PATH', default=None
    )
    parser.add_argument(
        '-m', '--installation_method', required=False,
        help='Choose how to install CloudWatch plugin in collectd',
        choices=['recommended', 'add', 'not_modify'],
        metavar='recommended|add|not_modify', default=None
    )
    parser.add_argument(
        '-g', '--push_asg', required=False,
        help='Include the Auto-Scaling Group name as a metric dimension:',
        default=None, action='store_true'
    )
    parser.add_argument(
        '-c', '--push_constant', required=False,
        help='Include the FixedDimension as a metric dimension',
        default=None, action='store_true'
    )
    parser.add_argument(
        '-v', '--dimension_value', required=False,
        help='FixedDimension value',
        metavar='DIMENSION_VALUE', default=None
    )
    parser.add_argument(
        '-d', '--debug', default=False,
        action='store_true', help='Provides verbose logging of metrics emitted to CloudWatch'
    )

    args = parser.parse_args()
    non_interactive = args.non_interactive
    host = args.host_name
    region = args.region
    proxy_name = args.proxy_name
    proxy_port = args.proxy_port
    access_key = args.access_key
    secret_key = args.secret_key
    creds_path = args.creds_path
    installation_method = args.installation_method
    push_asg = args.push_asg
    push_constant = args.push_constant
    dimension_value = args.dimension_value
    debug = args.debug

    def install_plugin():
        try:
            install_packages(SYSTEM_DEPENDENCIES)
            install_python_packages(PYTHON_DEPENDENCIES)
            create_directory_structure()
            chdir(TEMP_DIRECTORY)
            _run_command(DOWNLOAD_PLUGIN_CMD, shell=True, exit_on_failure=True)
            _run_command(UNTAR_PLUGIN_CMD, exit_on_failure=True)
            _run_command(COPY_PLUGIN_CMD, shell=True, exit_on_failure=True)
            supply_config()
            restart_collectd()
        finally:
            remove_temp_dir()

    def create_directory_structure():
        try:
            make_dirs(TEMP_DIRECTORY)
            make_dirs(CollectdInfo.PLUGINS_DIR)
        except IOError:
            raise InstallationFailedException("Cannot create required directories.")

    def supply_config():
        if COLLECTD_INFO.is_supported_version():
            _run_command(COPY_PLUGIN_INCLUDE_FILE_CMD, shell=True)
            config = PluginConfig()
            _prepare_plugin_config(config)
            if config.use_recommended_collectd_config:
                _copy_recommended_configs()
            elif config.only_add_plugin:
                _inject_plugin_configuration()
            else:
                print Color.yellow("Please find instructions for the manual configuration of the plugin in the readme.md file.")
        else:
            raise InstallationFailedException("The minimum supported version of collectd is " + CollectdInfo.MIN_SUPPORTED_VERSION + \
                                              ", and your version is " + COLLECTD_INFO.version + \
                                              ". You need to upgrade collectd before proceeding with the plugin installation.")

    def _prepare_plugin_config(plugin_config):
        metadata_reader = MetadataReader()
        InteractiveConfigurator(plugin_config, metadata_reader, COLLECTD_INFO, non_interactive, region, host,
                                proxy_name, proxy_port, access_key, secret_key, creds_path,installation_method, push_asg,
                                push_constant, dimension_value, debug).run()
        PluginConfigWriter(plugin_config).write()

    def _inject_plugin_configuration():
        if _is_cloudwatch_plugin_configured():
            print Color.yellow("CloudWatch collectd plugin is already configured in the existing collectd.conf file.")
        elif _can_safely_add_python_plugin():
            with open(COLLECTD_INFO.config_path, "a") as config:
                config.write(PLUGIN_CONFIGURATION_INCLUDE_LINE)
        else:
            print Color.yellow("Cannot add CloudWatch collectd plugin automatically to the existing collectd configuration.\n"
                               "Plugin must be configured manually, please find instructions in readme.md file.")

    def _copy_recommended_configs():
        _run_command(BACKUP_COLLECTD_CONFIG_CMD)
        _run_command(COPY_RECOMMENDED_COLLECTD_CONFIG_CMD, shell=True)
        _run_command(REPLACE_WHITELIST_CMD, shell=True)

    def _can_safely_add_python_plugin():
        configs = [COLLECTD_INFO.config_path]
        configs += _find_custom_includes(COLLECTD_INFO.config_path)
        return not any(_is_python_plugin_configured(config) for config in configs)

    def _is_cloudwatch_plugin_configured():
        with open(COLLECTD_INFO.config_path) as config:
            return bool(CLOUD_WATCH_COLLECTD_DETECTION_REGEX.findall(config.read()))

    def _find_custom_includes(config_path):
        with open(config_path) as config:
            return COLLECTD_CONFIG_INCLUDE_REGEX.findall(config.read())

    def _is_python_plugin_configured(config_path):
        with open(config_path) as config:
            return bool(COLLECTD_PYTHON_PLUGIN_CONFIGURATION_REGEX.findall(config.read()))

    def restart_collectd():
        _run_command(STOP_COLLECTD_CMD)
        _run_command(START_COLLECTD_CMD, exit_on_failure=True)

    def remove_temp_dir():
        shutil.rmtree(TEMP_DIRECTORY, ignore_errors=True)

    def _run_command(command, exit_on_failure=False, shell=False):
        Command(command.cmd, command.msg, shell=shell, exit_on_failure=exit_on_failure).run()

    install_plugin()


if __name__ == "__main__":
    if os.getuid() != ROOT_UID:
        exit(Color.red("Error: this script must be executed with elevated permissions."))
    try:
        main()
    except InstallationFailedException as e:
        exit(Color.red(str(e)))
