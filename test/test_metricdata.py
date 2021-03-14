import unittest

from time import sleep
from cloudwatch.modules.metricdata import MetricDataStatistic
import cloudwatch.modules.awsutils as awsutils


class MetricDataTest(unittest.TestCase):
    
    def test_metric_data_default_constructor(self):
        metric = MetricDataStatistic()
        assert_metric_data(metric)
        self.assertTrue(metric.timestamp)
        
    def test_metric_object_with_custom_value(self):
        new_metric_name = "Plugin1-Metric1"
        new_timestamp = awsutils.get_aws_timestamp()
        new_unit="Seconds"
        new_dimensions = {'Host':'InstanceID'}
        new_namespace = "test_namespace"
        metric = MetricDataStatistic(metric_name=new_metric_name, timestamp=new_timestamp,
                                     unit=new_unit, dimensions=new_dimensions, namespace=new_namespace)
        assert_metric_data(metric, new_metric_name, new_timestamp, new_unit,
                           new_dimensions, namespace=new_namespace)
        
    def test_empty_metric_object(self):
        metric = MetricDataStatistic()
        assert_metric_data(metric, metric_name="", unit="", dimensions={}, statistics=None, 
                           timestamp=None, namespace=MetricDataStatistic.NAMESPACE)
        
    def test_metric_object_with_statistic_data(self):
        new_statistics = MetricDataStatistic.Statistics(10)
        metric = MetricDataStatistic(statistic_values=new_statistics)
        assert_metric_data(metric, statistics=new_statistics)        
    
    def test_create_statistic_object_with_value(self):
        value = 400
        statistics = MetricDataStatistic.Statistics(value)
        assert_statistics(statistics, min=value, max=value, sum=value, sample_count=1)
        
    def test_statistic_values_add_value(self):
        statistics = MetricDataStatistic.Statistics(10)
        statistics._add_value(20)
        statistics._add_value(30)
        assert_statistics(statistics, min=10, max=30, sum=60, sample_count=3)

    def test_statistic_values_add_value2(self):
        statistics = MetricDataStatistic.Statistics(10)
        statistics._add_value(30)
        statistics._add_value(20)
        assert_statistics(statistics, min=10, max=30, sum=60, sample_count=3)
    
    def test_statistic_values_add_value3(self):
        statistics = MetricDataStatistic.Statistics(30)
        statistics._add_value(-10)
        statistics._add_value(20)
        assert_statistics(statistics, min=-10, max=30, sum=40, sample_count=3)
        
    def test_metric_data_creates_statistic_on_add_value(self):
        metric = MetricDataStatistic()
        self.assertFalse(metric.statistics)
        metric.add_value(10)
        self.assertTrue(metric.statistics)
        assert_statistics(metric.statistics, min=10, max=10, sum=10, sample_count=1)
    
    def test_metric_data_calculates_statistic_on_add_value(self):
        metric = MetricDataStatistic()
        metric.add_value(10)
        metric.add_value(-20)
        metric.add_value(30)
        assert_statistics(metric.statistics, min=-20, max=30, sum=20, sample_count=3)
    
    def test_metric_data_gets_current_timestamp(self):
        metric1 = MetricDataStatistic("metric_name", 20)
        sleep(1)
        metric2 = MetricDataStatistic("metric_name", 30)
        self.assertFalse(metric1.timestamp is metric2.timestamp)
        
    def test_custom_timestamp_is_not_overriden(self):
        timestamp = awsutils.get_aws_timestamp()
        metric1 = MetricDataStatistic("metric_name", 20, timestamp=timestamp)
        sleep(1)
        metric2 = MetricDataStatistic("metric_name", 20, timestamp=timestamp)
        self.assertTrue(metric1.timestamp is metric2.timestamp)


def assert_metric_data(metric_data, metric_name='', timestamp=None, unit="", dimensions={}, statistics=None, namespace=MetricDataStatistic.NAMESPACE):
    assert namespace == metric_data.namespace
    assert metric_name == metric_data.metric_name
    assert unit == metric_data.unit
    assert dimensions == metric_data.dimensions
    assert statistics == metric_data.statistics
    if timestamp is None:
        assert metric_data.timestamp  # Make sure that timestamp is not empty
    else:
        assert timestamp == metric_data.timestamp


def assert_statistics(statistics, min=None, max=None, sum=None, sample_count=1):
    assert min == statistics.min
    assert max == statistics.max
    assert sum == statistics.sum
    assert sample_count == statistics.sample_count
