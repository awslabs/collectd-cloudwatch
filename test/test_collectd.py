import unittest

import cloudwatch.modules.collectd as collectd


class collectdTest(unittest.TestCase):
        
    def test_stub_logging_methods_are_not_throwing_exceptions(self):
        collectd.debug("msg")
        collectd.info("msg")
        collectd.warning("msg")
        collectd.error("msg")
            
    def test_stub_callbacks_are_not_throwing_exceptions(self):
        collectd.register_config()
        collectd.register_init()
        collectd.register_write()
