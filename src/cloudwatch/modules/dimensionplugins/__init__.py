"""
This Dimension Plugin abstract base class file
"""

class DimensionPlugin(object):
    """
    Base class of Dimension plugin.
    Any vendor can implement a derived class
    """
    def __init__(self, config_helper, vl):
        self.func = None
        self.args = None
        self.config = config_helper
        self.vl = vl

    def __str__(self):
        if self.func and self.args:
            return "func: %s, args: %s" % (self.func.__name__, self.args)
        else:
            return __name__

    """
    Abstract method: register dimension plugin function
    """
    def register_plugin(self):
        pass

from generic_dimensions import *

