import re
import os

from ..logger.logger import get_logger


class ReaderUtils(object):
    
    _LOGGER = get_logger(__name__)
    _COMMENT_CHARACTER = '#'
    
    def __init__(self, path):
        self.path = path
        if not os.path.exists(path):
            raise IOError("Configuration file does not exist at: " + path)
    
    def get_string(self, key):
        return self._find_value_by_key(key)
    
    def get_boolean(self, key):
        value = self._find_value_by_key(key)
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        raise ValueError("Provided configuration value '" + value + "' does not specify boolean value.")

    def try_get_boolean(self, key, default_value):
        try:
            return self.get_boolean(key)
        except ValueError:
            return default_value

    def _find_value_by_key(self, key):
        config_list = self._load_config_as_list(self.path)
        for entry in config_list: 
            if not entry or entry[0] == self._COMMENT_CHARACTER:
                continue  # skip empty and commented lines
            try: 
                entry_key, entry_value = entry.split('=', 1)
                entry_key = entry_key.strip()
                if entry_key == key:
                    return self._strip_quotes(entry_value.strip()).strip()
            except:
                self._LOGGER.error("Cannot read configuration entry: " + str(entry))
                raise ValueError("Invalid syntax for entry '" + entry + "'.")
        return ""
    
    def _strip_quotes(self, string):
        return re.sub(r"^'|'$|^\"|\"$", '', string)
    
    def _load_config_as_list(self, path):
        """ 
        This method reads the configuration file and generates a list required by _parse_config_file 
        """
        return open(path).read().split('\n')
