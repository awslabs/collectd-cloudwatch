import unittest
import cloudwatch.modules.collectd as collectd

from mock import Mock
from cloudwatch.modules.logger.logger import get_logger, _Logger, _CollectdLogger


class LoggerTest(unittest.TestCase):
        
    def setUp(self):
        self.logger = get_logger(__name__)
        self.expected_prefix = "[AmazonCloudWatchPlugin][" + __name__ + "] "
    
    def test_type_of_logger(self):
        self.assertTrue(type(self.logger) is _CollectdLogger)
    
    def test_base_logger_is_abstract(self):
        self.assertTrue(type(_Logger()) is not _CollectdLogger)
        self.assertTrue(type(_Logger()) is _Logger)

    def test_debug_called_on_collectd(self):
        msg = "debug msg"
        collectd.debug = Mock()
        self.logger.debug(msg)
        self.assertTrue(collectd.debug.called)
        collectd.debug.assert_called_with(self.expected_prefix + msg)    
        
    def test_info_called_on_collectd(self):
        msg = "info msg"
        collectd.info = Mock()
        self.logger.info(msg)
        self.assertTrue(collectd.info.called)
        collectd.info.assert_called_with(self.expected_prefix + msg)
        
    def test_warning_called_on_collectd(self):
        msg = "warning msg"
        collectd.warning = Mock()
        self.logger.warning(msg)
        self.assertTrue(collectd.warning.called)
        collectd.warning.assert_called_with(self.expected_prefix + msg)
        
    def test_error_called_on_collectd(self):
        msg = "error msg"
        collectd.error = Mock()
        self.logger.error(msg)
        self.assertTrue(collectd.error.called)
        collectd.error.assert_called_with(self.expected_prefix + msg)
