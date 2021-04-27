from logger.logger import get_logger
from dimensionplugins import *
from configuration.dimensionreader import DimensionConfigReader

class Dimensions(object):
    """
    The Dimensions is responsible for holding all dimension plugins
    """
    _LOGGER = get_logger(__name__)

    def __init__(self, config_helper, vl):
        self.config = config_helper
        self.vl = vl
        self.dimension_handlers = dict()
        self.dimension_handlers["InstanceId"] = Dimension_InstanceId(self.config, self.vl)
        self.dimension_handlers["PluginInstance"] = Dimension_PluginInstance(self.config, self.vl)
        self.dimension_handlers["Hostname"] = Dimension_Hostname(self.config, self.vl)
        for h in self.dimension_handlers:
            self.dimension_handlers[h].register_plugin()

    """
    Go through the configured dimension list and find out if there is a plugin can handle it
    """
    def get_dimensions(self):
        dimension_config_list = DimensionConfigReader(self.config.DIMENSION_CONFIG_PATH).get_dimension_list()
        dimensions = dict()
        for dm in dimension_config_list:
            if dm in self.dimension_handlers:
                self.dimension_handlers[dm].func(dimensions, self.dimension_handlers[dm].args)
        return dimensions

