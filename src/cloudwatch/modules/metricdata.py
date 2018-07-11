import awsutils as awsutils
import plugininfo
import datetime

class MetricDataStatistic(object):
    """
    The MetricDataStatistic object encapsulates the information sent with putMetricData.
    
    Keyword arguments:
    namespace -- the default name space for CloudWatch metric (default defined by NAMESPACE)
    metric_name -- the metric identifier (default '')
    timestamp -- the time stamp in AWS format (default current date-time)
    value -- the raw metric value (default None)
    statistics -- the MetricDataStatistic.Statistics object used to aggregate raw values (default None)
    """
    NAMESPACE = plugininfo.NAMESPACE
    
    def __init__(self, metric_name='', unit="", dimensions={}, statistic_values=None,
                 timestamp=None, namespace=NAMESPACE):
        """ Constructor """
        self.namespace = namespace
        self.metric_name = metric_name
        self.unit = unit
        self.dimensions = dimensions
        self.statistics = statistic_values
        if timestamp:
            self.timestamp = timestamp
        else:
            self.timestamp = awsutils.get_aws_timestamp() 
        self.ds_type = None
        self.interval = None
        self.last_update = None
        self.last_value = None
        
    def cumulative(self, ds_type=None, interval=None, last_update=None, last_value=None):
        if ds_type:
            self.ds_type = ds_type
        if interval:
            self.interval = interval
        if last_update:
            self.last_update = last_update
        if last_value:
            self.last_value = last_value

    def add_value(self, value, time=None):

        if self.ds_type in ['derive', 'counter']:
            if self.last_update is None or self.last_value is None or \
               self.interval and time - self.last_update > 2*self.interval or \
               time - self.last_update == 0:
                self.last_update, self.last_value = time, value
                return

            self.last_update, self.last_value, value = \
                time, value, (value - self.last_value)/(time - self.last_update)
            if self.ds_type == 'counter':
                if value < 0:
                    value += 2**32 - 1
                if value < 0:
                    value += 2**64 - 2**32
        else:
            self.last_update, self.last_value = time, value

        if not self.statistics:
            self.statistics = self.Statistics(value) 
        else:
            self.statistics._add_value(value)
        
    class Statistics:
        """
        The Statistics object encapsulates the aggregated metric values used by MetricDataStatistic.
        
        Keyword arguments:
        min -- the minimum aggregated value (default None)
        max -- the maximum aggregated value (default None)
        sum -- the sum of all aggregated values (default None)
        avg -- the average of all aggregated values (default None)
        sample_count -- the count of aggregated values (default 0)
        """
        
        def __init__(self, value):
            """ Constructor """
            self.min = value
            self.max = value
            self.sum = value
            self.sample_count = 1
        
        def _add_value(self, value):
            """ 
            Add new value and recalculate the statistics
            
            Keyword arguments:
            value -- new value to be included in the statistics
            """
            if value > self.max:
                self.max = value
            if value < self.min:
                self.min = value
            self.sum += value
            self.sample_count += 1


class MetricDataBuilder(object):
    """
    The metric data builder is responsible for translating Collectd value list objects
    to CloudWatch MetricData.
    
    Keyword arguments:
    config_helper -- The ConfigHelper object with configuration loaded
    vl -- The Collectd ValueList object with metric information
    adjusted_time - The adjusted_time is the time adjusted according to storage resolution
    """
    
    def __init__(self, config_helper, vl, adjusted_time=None):
        self.config = config_helper
        self.vl = vl
        self.adjusted_time = adjusted_time
        self.ds_type = None
        if vl.meta and 'ds_type' in vl.meta:
            self.ds_type = vl.meta['ds_type']

    def build(self):
        """ Builds metric data object with name and dimensions but without value or statistics """
        metric_array = [MetricDataStatistic(metric_name=self._build_metric_name(), dimensions=self._build_metric_dimensions(), timestamp=self._build_timestamp())]
        if self.config.push_asg:
            metric_array.append(MetricDataStatistic(metric_name=self._build_metric_name(), dimensions=self._build_asg_dimension(), timestamp=self._build_timestamp()))
        if self.config.push_constant:
            metric_array.append(MetricDataStatistic(metric_name=self._build_metric_name(), dimensions=self._build_constant_dimension(), timestamp=self._build_timestamp()))
        if self.ds_type:
            for metric in metric_array:
                metric.cumulative(ds_type=self.ds_type, interval=self.vl.interval)
        return metric_array
        
    def _build_timestamp(self):
        return datetime.datetime.utcfromtimestamp(self.adjusted_time).strftime('%Y%m%dT%H%M%SZ') if self.config.enable_high_resolution_metrics else None

    def _build_metric_name(self): 
        """
        Creates single string metric name from the Collectd ValueList naming format by flattening the
        multilevel structure into the string in the following format: "plugin.type.type_instance".
        The not required name parts (type_instance) will be skipped if empty.
        """
        name_builder = [str(self.vl.plugin)]
        name_builder.append(str(self.vl.type))
        if self.vl.type_instance:
            name_builder.append(str(self.vl.type_instance))
        return ".".join(name_builder)
    
    def _build_asg_dimension(self):
        dimensions = {
              "AutoScalingGroup" : self._get_autoscaling_group(),
              "PluginInstance" : self._get_plugin_instance_dimension()
              }
        return dimensions

    def _build_constant_dimension(self):
        dimensions = {
              "FixedDimension" : self.config.constant_dimension_value,
              "PluginInstance" : self._get_plugin_instance_dimension()
              }
        return dimensions

    def _build_metric_dimensions(self):
        dimensions = {
              "Host" : self._get_host_dimension(),
              "PluginInstance" : self._get_plugin_instance_dimension()
              }
        if self.config.push_asg:
            dimensions["AutoScalingGroup"] = self._get_autoscaling_group()
        if self.config.push_constant:
            dimensions["FixedDimension"] = self.config.constant_dimension_value
        return dimensions

    def _get_plugin_instance_dimension(self):
        if self.vl.plugin_instance:
            return self.vl.plugin_instance
        return "NONE"

    def _get_host_dimension(self):
        if self.config.host:
            return self.config.host
        return self.vl.host

    def _get_autoscaling_group(self):
        if self.config.asg_name:
            return self.config.asg_name
        return "NONE"
