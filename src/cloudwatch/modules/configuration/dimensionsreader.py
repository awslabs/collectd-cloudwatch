from readerutils import ReaderUtils
from ..logger.logger import get_logger


class DimensionsReader(object):
    """
    The dimensions file reader class that is responsible for reading and parsing file containing AWS dimensions.
    
    The credentials file is a simple text file in format:
    dimension1
    dimension2
    
    Keyword arguments:
    dimensions_path -- the path for the credentials file to be parsed (Required)
    """

    _LOGGER = get_logger(__name__)

    def __init__(self, dimensions_path):
        self.dimensions_path = dimensions_path
        self.dimensions = None
        try:
            self.reader_utils = ReaderUtils(dimensions_path)
            self._parse_dimensions_file()
        except Exception as e:
            self._LOGGER.warning("Cannot read AWS dimensions from file. Defaulting to default dimensions.")

    def _parse_dimensions_file(self):
        """ 
        This method retrieves values form preprocessed configuration list 
        in format: 
        value 
        value2 
        """
        dimensions_list = self.reader_utils.get_dimensions()
        if not dimensions_list:
            self._LOGGER.warning("Cannot read AWS dimensions from file. Defaulting to default dimensions.")
        self.dimensions = dimensions_list
  
class DimensionsReaderException(Exception):
    pass