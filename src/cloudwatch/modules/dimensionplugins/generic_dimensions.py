"""
This is the file containing generic dimension plugin classes
"""

from . import DimensionPlugin

def dimension_get_instance_id(dimension, args):
    dimension[args['name']] = args['value']

"""
This InstanceId Dimension coming from configured host instance
"""
class Dimension_InstanceId(DimensionPlugin):
    def register_plugin(self):
        self.func = dimension_get_instance_id
        self.args = {
            'name': "InstanceId",
            'value': self.config.host
        }


def dimension_get_plugin_instance(dimension, args):
    dimension[args['name']] = args['value']

"""
This PluginInstance Dimension coming from collectd value plugin instance
"""
class Dimension_PluginInstance(DimensionPlugin):
    def register_plugin(self):
        self.func = dimension_get_plugin_instance
        self.args = {
            'name': "PluginInstance",
            'value': self.vl.plugin_instance
        }

