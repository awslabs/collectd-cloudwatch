"""
This is the file containing generic dimension plugin classes
"""

import os
from . import DimensionPlugin

"""
This InstanceId Dimension coming from configured host instance
"""

def dimension_get_instance_id(dimension, args):
    dimension[args['name']] = args['value']

class Dimension_InstanceId(DimensionPlugin):
    def register_plugin(self):
        self.func = dimension_get_instance_id
        self.args = {
            'name': "InstanceId",
            'value': self.config.host
        }


"""
This PluginInstance Dimension coming from collectd value plugin instance
"""

def dimension_get_plugin_instance(dimension, args):
    dimension[args['name']] = args['value']

class Dimension_PluginInstance(DimensionPlugin):
    def register_plugin(self):
        self.func = dimension_get_plugin_instance
        plugin_instance = self.vl.plugin_instance if self.vl.plugin_instance else "NONE"
        self.args = {
            'name': "PluginInstance",
            'value': plugin_instance
        }


"""
Hostname Dimension report the hostname value
"""

def dimension_get_hostname(dimension, args):
    dimension[args['name']] = args['value']

class Dimension_Hostname(DimensionPlugin):
    def register_plugin(self):
        self.func = dimension_get_hostname
        self.args = {
            'name': "Hostname",
            'value': os.uname()[1]
        }
