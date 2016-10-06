"""
CollectdCloudWatchPlugin plugin
"""
try:
    import collectd # this will be in python path when running from collectd
except:
    import cloudwatch.modules.collectd as collectd
import traceback

from cloudwatch.modules.configuration.confighelper import ConfigHelper
from cloudwatch.modules.flusher import Flusher
from cloudwatch.modules.logger.logger import get_logger

_LOGGER = get_logger(__name__)


def aws_init():
    """
    Collectd callback entry used to initialize plugin
    """
    try:
        config = ConfigHelper()
        flusher = Flusher(config)
        collectd.register_write(aws_write, data = flusher)
        _LOGGER.info('Initialization finished successfully.')
    except Exception as e:
        _LOGGER.error("Cannot initialize plugin. Cause: " + str(e) + "\n" + traceback.format_exc())


def aws_write(vl, flusher):
    """ 
    Collectd callback entry used to write metric data
    """
    flusher.add_metric(vl)
    
collectd.register_init(aws_init)
