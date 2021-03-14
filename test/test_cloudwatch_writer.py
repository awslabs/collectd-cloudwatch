import unittest
import cloudwatch_writer as plugin

from mock import patch, Mock, MagicMock 


class CloudWatchWriter(unittest.TestCase):
    
    def setUp(self):
        plugin._LOGGER = MagicMock()
        plugin._LOGGER.error = Mock()
        plugin._LOGGER.info = Mock()
    
    @patch("cloudwatch_writer.ConfigHelper")
    @patch("cloudwatch_writer.Flusher")
    def test_initialize_plugin_without_exceptions(self, config_helper, flusher):
        config_helper.return_value = MagicMock()
        flusher.return_value = MagicMock()
        plugin.aws_init()
    
    @patch("cloudwatch_writer.ConfigHelper")
    @patch("cloudwatch_writer.Flusher")
    def test_initialize_plugin_with_flusher_exception(self, config_helper, flusher):
        config_helper.return_value = MagicMock()
        flusher.side_effect = Exception("Cannot initialize flusher.")
        plugin.aws_init()
        self.assertTrue(plugin._LOGGER.error.called)
    
    @patch("cloudwatch_writer.ConfigHelper")
    @patch("cloudwatch_writer.Flusher")
    def test_initialize_plugin_with_config_IO_error(self, config_helper, flusher):
        config_helper.side_effect = IOError("Cannot load configuration file.")
        flusher.side_effect = MagicMock()
        plugin.aws_init()
        self.assertTrue(plugin._LOGGER.error.called)
        
    @patch("cloudwatch_writer.ConfigHelper")
    @patch("cloudwatch_writer.Flusher")
    def test_initialize_plugin_with_config_value_error(self, config_helper, flusher):
        config_helper.side_effect = ValueError("Inconsistent configuration detected.")
        flusher.side_effect = MagicMock()
        plugin.aws_init()
        self.assertTrue(plugin._LOGGER.error.called)
    
    @patch("cloudwatch_writer.ConfigHelper")
    @patch("cloudwatch_writer.Flusher")
    def test_write_passes_vl_to_flusher(self, config_helper, flusher_class):
        config_helper.return_value = MagicMock()
        flusher = MagicMock()
        flusher.add_metric = Mock()
        flusher_class.return_value = flusher
        plugin.aws_init()
        vl = MagicMock()
        plugin.aws_write(vl, flusher)
        flusher.add_metric.assert_called_with(vl)
