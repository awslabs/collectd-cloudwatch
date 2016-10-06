import abc
try:
    import collectd
except:
    from .. import collectd


def get_logger(channel=None):
    """
    Provides the default logger for the application.
    """
    return _CollectdLogger(channel)


class _Logger(object):
    """
    The base class for logger, all loggers have to extend this class and provide implementation for the basic logging methods.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod    
    def debug(self, msg):
        pass
    
    @abc.abstractmethod
    def info(self, msg):
        pass
    
    @abc.abstractmethod
    def warning(self, msg):
        pass
    
    @abc.abstractmethod
    def error(self, msg):
        pass


class _CollectdLogger(_Logger):
    """
    The wrapper class for Collectd logging functionalities.
    """
    _PLUGIN = "AmazonCloudWatchPlugin" 

    def __init__(self, channel):
        self.collectd = collectd
        self.channel = channel
        self.prefix = self._build_prefix()
    
    def _build_prefix(self):
        """
        Creates a prefix which will be attached to each message passed through this logger.
        Format example: "[AmazonCloudWatchPlugin][cloudwatch.modules.client.putclient] "
        """
        prefix = []
        if _CollectdLogger._PLUGIN:
            prefix.append("[" + _CollectdLogger._PLUGIN + "]")
        if self.channel:
            prefix.append("[" + self.channel + "]")
        return "".join(prefix) + " "
    
    def debug(self, msg):
        collectd.debug(self.prefix + msg)
    
    def info(self, msg):
        collectd.info(self.prefix + msg)
    
    def warning(self, msg):
        collectd.warning(self.prefix + msg)
    
    def error(self, msg):
        collectd.error(self.prefix + msg)