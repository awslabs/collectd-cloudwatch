import unittest

from cloudwatch.modules.client.querystringbuilder import QuerystringBuilder
from cloudwatch.modules.metricdata import MetricDataStatistic

class QuerystringBuilderTest(unittest.TestCase):
    
    def setUp(self):
        self.builder = QuerystringBuilder(None)
        
    def test_build_metric_map_for_single_metric_without_dimensions(self):
        metric = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20))
        metric_map = self.builder._build_metric_map([metric])
        assert_metric_map([metric], metric_map)
        
    def test_build_metric_map_for_multiple_metrics_without_dimensions(self):
        metric1 = MetricDataStatistic("Metric1", statistic_values=MetricDataStatistic.Statistics(20))
        metric2 = MetricDataStatistic("Metric2", statistic_values=MetricDataStatistic.Statistics(30))
        metric_list = [metric1, metric2]
        metric_map = self.builder._build_metric_map(metric_list)
        assert_metric_map(metric_list, metric_map)
        
    def test_build_metric_map_for_single_metric_with_dimensions(self):
        dimensions = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20), dimensions=dimensions)   
        metric_map = self.builder._build_metric_map([metric])
        assert_metric_map([metric], metric_map)
    
    def test_build_metric_map_for_multiple_metrics_with_dimensions(self):
        dimensions1 = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric1 = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20), dimensions=dimensions1)   
        dimensions2 = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric2 = MetricDataStatistic("test_metric2", statistic_values=MetricDataStatistic.Statistics(400), dimensions=dimensions2)   
        metric_list = [metric1, metric2]
        metric_map = self.builder._build_metric_map(metric_list)
        assert_metric_map(metric_list, metric_map)
        
    def test_build_querystring_with_no_metrics(self):
        querystring = self.builder.build_querystring([], get_canonical_map())
        assert_querystring(get_canonical_map(), querystring)
        
    def test_build_querystring_with_one_metric(self):
        dimensions = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20), dimensions=dimensions)
        expected_map = get_canonical_map()
        expected_map.update(self.builder._build_metric_map([metric]))
        querystring = self.builder.build_querystring([metric], get_canonical_map())
        assert_querystring(expected_map, querystring)
        
    def test_build_querystring_with_multiple_metrics(self):
        dimensions1 = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric1 = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20), dimensions=dimensions1)   
        dimensions2 = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric2 = MetricDataStatistic("test_metric2", statistic_values=MetricDataStatistic.Statistics(400), dimensions=dimensions2)
        expected_map = get_canonical_map()
        expected_map.update(self.builder._build_metric_map([metric1, metric2]))
        querystring = self.builder.build_querystring([metric1, metric2], get_canonical_map())
        assert_querystring(expected_map, querystring)

    def test_build_querystring_with_storage_resolution(self):
        self.builder = QuerystringBuilder(True)
        dimensions1 = {"Dimension1": 20, "Dimension2": 30, "Host": "localhost"}
        metric1 = MetricDataStatistic("test_metric", statistic_values=MetricDataStatistic.Statistics(20), dimensions=dimensions1)
        querystring = self.builder.build_querystring([metric1], get_canonical_map())
        self.assertTrue(self.builder._STORAGE_RESOLUTION in querystring)

    def test_build_map_with_statistics(self):
        dimensions1 = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric = MetricDataStatistic("test_metric", dimensions=dimensions1)
        metric.add_value(10)
        metric.add_value(20)
        metric.add_value(40)
        map = {}
        prefix = "metric_prefix"
        self.builder._add_values(metric, map, prefix)
        self.assertEquals(10, map[prefix + QuerystringBuilder._STAT_MIN])
        self.assertEquals(40, map[prefix + QuerystringBuilder._STAT_MAX])
        self.assertEquals(70, map[prefix + QuerystringBuilder._STAT_SUM])
        self.assertEquals(3, map[prefix + QuerystringBuilder._STAT_SAMPLE])
    
    def test_build_querystring_with_statistics(self):
        dimensions = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric = MetricDataStatistic("test_metric", dimensions=dimensions)
        metric.add_value(10)
        metric.add_value(-20)
        metric.add_value(50)
        expected_map = get_canonical_map()
        expected_map.update(self.builder._build_metric_map([metric]))
        querystring = self.builder.build_querystring([metric], get_canonical_map())
        self.assertTrue(QuerystringBuilder._STAT_MAX +"=50" in querystring)
        self.assertTrue(QuerystringBuilder._STAT_MIN +"=-20" in querystring)
        self.assertTrue(QuerystringBuilder._STAT_SUM +"=40" in querystring)
        self.assertTrue(QuerystringBuilder._STAT_SAMPLE +"=3" in querystring)
        
    def test_build_map_without_statistics(self):
        dimensions = { "Dimension1": 20, "Dimension2": 30, "Host": "localhost" }
        metric = MetricDataStatistic("test_metric", dimensions=dimensions)
        map = {}
        prefix = "metric_prefix"
        with self.assertRaises(ValueError):
            self.builder._add_values(metric, map, prefix)
        
    def test_no_double_slash_url_encoding(self):
        """ when string is urlencoded twice or more the slash character gets invalid value of %252F instead of %2F """
        input_map = {"test":"test/test"}
        querystring = self.builder.build_querystring([], input_map)
        self.assertTrue("%2F" in querystring)
        self.assertFalse("%252F" in querystring)
        
    def test_spaces_are_urlencoded(self):
        """ the standard urllib.urlencode encodes spaces as '+', but CloudWatch requires '%20' """
        input_map = {"test":"test test2"}
        querystring = self.builder.build_querystring([], input_map)
        self.assertEquals("test=test%20test2", querystring)
        self.assertFalse('+' in querystring)
        
    def test_plus_is_encoded_properly(self):
        input_map = {"test":"test+test2"}
        querystring = self.builder.build_querystring([], input_map)
        self.assertEquals("test=test%2Btest2", querystring)
        self.assertFalse('+' in querystring)
        
def get_canonical_map():
    return {"Action": "test_action",
            "Namespace": "test_namespace",
            "Version": "test_version",
            "X-Amz-Algorithm": "test_algorithm",
            "X-Amz-Credential": "access_key"
        }

def split_querystring(querystring):
    list = querystring.split('&')
    request_list = []
    for item in list:
        request_list.append(item.split('=', 1))
    return request_list

def assert_querystring(expected_map, querystring):
    keys_in_order = sorted(expected_map.keys())
    splited_querystring = split_querystring(querystring) 
    assert len(expected_map) == len(splited_querystring)
    for i in range(len(keys_in_order)):
        current_key = splited_querystring[i][0]
        current_value = splited_querystring[i][1]
        assert keys_in_order[i] == current_key
        try:
            current_value = int(current_value)
        except:
            pass
        assert expected_map[keys_in_order[i]] == current_value
        
def assert_metric_map(metric_list, metric_map):
    index = 1
    for metric in metric_list:
        prefix = "MetricData.member." + str(index) + "."
        assert metric.metric_name == metric_map[prefix + "MetricName"]
        assert metric.timestamp == metric_map[prefix + "Timestamp"]
        assert_dimensions(metric, index, metric_map)
        index += 1
    
def assert_dimensions(metric, metric_index, metric_map):
    dimension_index = 1
    for key in metric.dimensions.keys():
        prefix = "MetricData.member." + str(metric_index) + ".Dimensions.member." + str(dimension_index) + "."
        assert key == metric_map[prefix + "Name"]
        assert metric.dimensions[key] == metric_map[prefix + "Value"]
        dimension_index += 1