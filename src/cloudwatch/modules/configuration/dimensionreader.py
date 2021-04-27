from ..logger.logger import get_logger

class DimensionConfigReader(object):
    """
    The DimensionConfigReader is responsible for parsing the dimension.conf file into a dimension list
    used by the Dimension class.
    """
    _LOGGER = get_logger(__name__)

    def __init__(self, dimension_config_path):
        self.dimension_config_path = dimension_config_path

    def get_dimension_list(self):
        """
        Reads dimension configuration file and returns a list of dimension name.
        :return: dimension list configured
        """
        try:
            return self._get_dimensions_from_file(self.dimension_config_path)
        except IOError as e:
            self._LOGGER.warning("Could not open dimension file '" + self.dimension_config_path + "'. Reason: " + str(e))
            return None

    def _get_dimensions_from_file(self, dimension_path):
        dimensions = []
        with open(dimension_path) as dimension_file:
            lines = dimension_file.readlines()
            for line in lines:
                dimensions.append(line.rstrip())
        return dimensions




