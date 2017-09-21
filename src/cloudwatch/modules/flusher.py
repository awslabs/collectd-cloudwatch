import threading
import time
import os
import math

from client.putclient import PutClient
from logger.logger import get_logger
from metricdata import MetricDataStatistic, MetricDataBuilder

class Flusher(object):
    """
    The flusher is responsible for translating Collectd metrics to CloudWatch MetricDataStatistic, 
    batching, aggregating and flushing metrics to CloudWatch endpoints.
    
    Keyword arguments:
    config_helper -- The ConfigHelper object with configuration loaded
    """
    
    _LOGGER = get_logger(__name__)
    _FLUSH_INTERVAL_IN_SECONDS = 60
    _FLUSH_DELTA_IN_SECONDS = 1 
    _MAX_METRICS_PER_PUT_REQUEST = 20
    _MAX_METRICS_TO_AGGREGATE = 2000 

    def __init__(self, config_helper, dataset_resolver):
        self.lock = threading.Lock()
        self.client = None
        self.config = config_helper
        self.metric_map = {}
        self.last_flush_time = time.time()
        self.nan_key_set = set()
        self.enable_high_resolution_metrics = config_helper.enable_high_resolution_metrics
        self.flush_interval_in_seconds = int(config_helper.flush_interval_in_seconds if config_helper.flush_interval_in_seconds else self._FLUSH_INTERVAL_IN_SECONDS)
        self.max_metrics_to_aggregate = self._MAX_METRICS_PER_PUT_REQUEST if self.enable_high_resolution_metrics else self._MAX_METRICS_TO_AGGREGATE
        self.client = PutClient(self.config)
        self._dataset_resolver = dataset_resolver

    def is_numerical_value(self, value):
        """
        Assume that the value from collectd to this plugin is float or Integer, if string transfer from collectd to this interface,
        we should modify the method  _add_values_to_metric, to convert the string type value to float type value.

        Returns:
            True if the value is float and is not nan
            False if the value is nan
        """
        try:
            return not math.isnan(float(value))
        except ValueError:
            return False

    def _resolve_ds_names(self, value_list):
        ds_names = self._dataset_resolver.get_dataset_names(value_list.type)
        if not ds_names:
            return ['value{}'.format(i) for i in range(len(value_list.values))]

        return ds_names

    def _expand_value_list(self, value_list):
        if len(value_list.values) == 1:
            return [value_list]

        expanded = []
        for ds_name, value in zip(self._resolve_ds_names(value_list), value_list.values):
            new_value = value_list.__class__(
                host=value_list.host,
                plugin=value_list.plugin,
                plugin_instance=value_list.plugin_instance,
                type=value_list.type,
                type_instance=value_list.type_instance + '.{}'.format(ds_name) if value_list.type_instance else ds_name,
                time=value_list.time,
                interval=value_list.interval,
                meta=value_list.meta,
                values=[value]
            )
            expanded.append(new_value)

        return expanded

    def add_metric(self, value_list):
        """
        Translates Collectd metrics to CloudWatch format and stores them in flusher for further processing
        such as batching and aggregating.

        Keyword arguments:
        value_list -- The ValueList object passed by Collectd to the write callback
        """
        with self.lock:
            # The flush operation should take place before adding metric for a new minute.
            # Together with flush delta this ensures that old metrics are flushed before or at the start of a new minute.
            self._flush_if_need(time.time())
            for value in self._expand_value_list(value_list):
                if self.config.whitelist.is_whitelisted(self._get_metric_key(value)):
                        self._aggregate_metric(value)

    def _flush_if_need(self, current_time):
        """ 
        Checks if metrics should be flushed and starts the flush procedure
        """
        if self._is_flush_time(current_time):
            if self.config.debug and self.metric_map:
                state = ""
                for dimension_metrics in self.metric_map:
                    state += str(dimension_metrics) + "[" + str(self.metric_map[dimension_metrics][0].statistics.sample_count) + "] "
                self._LOGGER.info("[debug] flushing metrics " + state)
            self._flush()
    
    def _is_flush_time(self, current_time):
        if self.enable_high_resolution_metrics:
            return (current_time - self.last_flush_time) >= self.flush_interval_in_seconds + self._FLUSH_DELTA_IN_SECONDS
        return (current_time - self.last_flush_time) + self._FLUSH_DELTA_IN_SECONDS >= self.flush_interval_in_seconds

    def record_nan_value(self, key, value_list):
        if key not in self.nan_key_set:
            self._LOGGER.warning(
                "Adding Metric value is not numerical, key: " + key + " value: " + str(value_list.values))
            self.nan_key_set.add(key)

    def _aggregate_metric(self, value_list):
        """
        Selects existing metric or adds a new metric to the metric_map. Then aggregates values from ValueList with the selected metric.
        If the size of metric_map is above the limit, new metric will not be added and the value_list will be dropped.
        """
        nan_value_count = 0
        dimension_key = self._get_metric_key(value_list)
        adjusted_time = int(value_list.time)

        key = dimension_key
        if self.enable_high_resolution_metrics:
            key = dimension_key + "-" + str(adjusted_time)
        if key in self.metric_map:
            nan_value_count = self._add_values_to_metrics(self.metric_map[key], value_list)
        else:
            if len(self.metric_map) < self.max_metrics_to_aggregate:
                nan_value_count = self._add_metric_to_queue(value_list, adjusted_time, key)
            else:
                if self.enable_high_resolution_metrics:
                    if self.config.debug and self.metric_map:
                        state = ""
                        for dimension_metrics in self.metric_map:
                            state += str(dimension_metrics) + "[" + str(self.metric_map[dimension_metrics][0].statistics.sample_count) + "] "
                        self._LOGGER.info("[debug] flushing metrics " + state)
                    self._flush()
                    nan_value_count = self._add_metric_to_queue(value_list, adjusted_time, key)
                else:
                    self._LOGGER.warning("Batching queue overflow detected. Dropping metric.")
        if nan_value_count:
            self.record_nan_value(dimension_key, value_list)

    def _add_metric_to_queue(self, value_list, adjusted_time, key):
        nan_value_count = 0
        metrics = MetricDataBuilder(self.config, value_list, adjusted_time).build()
        nan_value_count = self._add_values_to_metrics(metrics, value_list)
        if nan_value_count != len(value_list.values):
            self.metric_map[key] = metrics
        return nan_value_count

    def _get_metric_key(self, value_list):
        """
        Generates key for the metric. The key must use both metric_name and plugin instance to ensure uniqueness.
        """ 
        return value_list.plugin + "-" + value_list.plugin_instance + "-" + value_list.type + "-" +value_list.type_instance

    def _add_values_to_metrics(self, dimension_metrics, value_list):
        """
        Aggregates values from value_list with existing metric
        Add the valid value to the metric and just skip the nan value.

        Returns:
            return the count of the nan value in value_list
        """
        
        for metric in dimension_metrics:
            nan_value_count = 0
            for value in value_list.values:
                if self.is_numerical_value(value):
                    metric.add_value(value)
                else:
                    nan_value_count += 1
        return nan_value_count

    def _flush(self):
        """
        Batches and puts metrics to CloudWatch
        """
        self.last_flush_time = time.time()
        metric_map_size = len(self.metric_map)
        if self.metric_map:
            prepare_batch = self._prepare_batch()
            try:
                while True:
                    metric_batch = prepare_batch.next()
                    if not metric_batch:
                        break
                    self.client.put_metric_data(MetricDataStatistic.NAMESPACE, metric_batch)
                    if len(metric_batch) < self._MAX_METRICS_PER_PUT_REQUEST:
                        break
            except StopIteration, e:
                if metric_map_size % self._MAX_METRICS_PER_PUT_REQUEST != 0 or len(self.metric_map) != 0:
                    self._LOGGER.error("_flush error: " + str(e) + "  Original map size: " + str(metric_map_size))

    def _prepare_batch(self):
        """
        Removes metrics from the metric_map and adds them to the batch. 
        The batch size is defined by _MAX_METRICS_PER_PUT_REQUEST.
        """
        metric_batch = []
        while self.metric_map:
            key, dimension_metrics = self.metric_map.popitem()
            for metric in dimension_metrics:
                if len(metric_batch) < self._MAX_METRICS_PER_PUT_REQUEST:
                    metric_batch.append(metric)
                else:
                    yield metric_batch
                    metric_batch = []
                    metric_batch.append(metric)
        yield metric_batch
