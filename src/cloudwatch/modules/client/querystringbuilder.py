import operator

from ..logger.logger import get_logger
from urllib import urlencode


class QuerystringBuilder(object):
    """
    The querystring builder is responsible for creating a querystring from MetricData objects 
    and additional request parameters.  
    """
    _LOGGER = get_logger(__name__)
    _METRIC_PREFIX = "MetricData.member."
    _DIMENSION_PREFIX = "Dimensions.member."
    _METRIC_NAME_KEY = "MetricName"
    _NAME_KEY = "Name"
    _VALUE_KEY = "Value"
    _TIMESTAMP_KEY = "Timestamp"
    _STATISTICS_KEY = "StatisticValues."
    _STAT_MAX = _STATISTICS_KEY + "Maximum"
    _STAT_MIN = _STATISTICS_KEY + "Minimum"
    _STAT_SUM = _STATISTICS_KEY + "Sum"
    _STAT_SAMPLE = _STATISTICS_KEY + "SampleCount"
   
    def build_querystring(self, metric_list, request_map):
        """
        Creates querystring from list of MetricData objects and a map of request key value pairs 
        with all keys sorted in ascending order as required by CloudWatch.
        """
        metric_map = self._build_metric_map(metric_list)
        request_map.update(metric_map)
        sorted_query_data = sorted(request_map.items(),key=operator.itemgetter(0))
        # by default urlencode replace spaces with '+' but CloudWatch requires them to be encoded to '%20'
        url_string = urlencode(sorted_query_data).replace('+', '%20') 
        return url_string

    def _build_metric_map(self, metric_list):
        """ 
        Translate the list of metric objects into a single map with keys represented in the format required 
        by CloudWatch querystring.
        """   
        metric_map = {}
        metric_index = 1
        for metric in metric_list:
            metric_prefix = self._METRIC_PREFIX + str(metric_index) + "."
            metric_map[metric_prefix + self._METRIC_NAME_KEY] = metric.metric_name
            metric_map[metric_prefix + self._TIMESTAMP_KEY] = metric.timestamp
            self._add_dimensions(metric, metric_map, metric_prefix)
            self._add_values(metric, metric_map, metric_prefix)
            metric_index += 1
        return metric_map
    
    def _add_dimensions(self, metric, metric_map, metric_prefix):
        dimension_index = 1
        for dimension_key in metric.dimensions.keys():
            dimension_prefix = metric_prefix + self._DIMENSION_PREFIX + str(dimension_index) + "."
            metric_map[dimension_prefix + self._NAME_KEY] = dimension_key
            metric_map[dimension_prefix + self._VALUE_KEY] = metric.dimensions[dimension_key]
            dimension_index += 1
    
    def _add_values(self, metric, metric_map, metric_prefix):
        if not metric.statistics:
            msg = "Missing value for metric " + metric.metric_name
            self._LOGGER.warning(msg)
            raise ValueError(msg)
        metric_map[metric_prefix + self._STAT_MAX] = metric.statistics.max
        metric_map[metric_prefix + self._STAT_MIN] = metric.statistics.min
        metric_map[metric_prefix + self._STAT_SUM] = metric.statistics.sum
        metric_map[metric_prefix + self._STAT_SAMPLE] = metric.statistics.sample_count
