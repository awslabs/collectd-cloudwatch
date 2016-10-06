import threading
import time
import os

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

    def __init__(self, config_helper):
        self.lock = threading.Lock()
        self.client = None
        self.config = config_helper
        self.metric_map = {}
        self.last_flush_time = time.time()

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
            if self.config.whitelist.is_whitelisted(self._get_metric_key(value_list)):
                self._aggregate_metric(value_list)

    def _flush_if_need(self, current_time):
        """ 
        Checks if metrics should be flushed and starts the flush procedure
        """
        if self._is_flush_time(current_time):
            if self.config.debug and self.metric_map:
                state = ""
                for metric in self.metric_map:
                    state += str(metric) + "[" + str(self.metric_map[metric].statistics.sample_count) + "] "
                self._LOGGER.info("[debug] flushing metrics " + state)
            self._flush()
    
    def _is_flush_time(self, current_time):
        return (current_time - self.last_flush_time) + self._FLUSH_DELTA_IN_SECONDS >= self._FLUSH_INTERVAL_IN_SECONDS
    
    def _aggregate_metric(self, value_list):
        """
        Selects existing metric or adds a new metric to the metric_map. Then aggregates values from ValueList with the selected metric.
        If the size of metric_map is above the limit, new metric will not be added and the value_list will be dropped.
        """
        key = self._get_metric_key(value_list)
        if key in self.metric_map:
            self._add_values_to_metric(self.metric_map[key], value_list)
        else:
            if len(self.metric_map) < self._MAX_METRICS_TO_AGGREGATE:
                metric = MetricDataBuilder(self.config, value_list).build()
                self.metric_map[key] = metric
                self._add_values_to_metric(metric, value_list)
            else:
                self._LOGGER.warning("Batching queue overflow detected. Dropping metric.")
            
    def _get_metric_key(self, value_list):
        """
        Generates key for the metric. The key must use both metric_name and plugin instance to ensure uniqueness.
        """ 
        return value_list.plugin + "-" + value_list.plugin_instance + "-" + value_list.type + "-" +value_list.type_instance
    
    def _add_values_to_metric(self, metric, value_list):
        """
        Aggregates values from value_list with existing metric
        """
        for value in value_list.values:
            metric.add_value(value)
    
    def _flush(self):
        """
        Batches and puts metrics to CloudWatch
        """
        self.last_flush_time = time.time()
        self.client = PutClient(self.config)
        while self.metric_map:
            metric_batch = self._prepare_batch()
            self.client.put_metric_data(MetricDataStatistic.NAMESPACE, metric_batch)

    def _prepare_batch(self):
        """
        Removes metrics from the metric_map and adds them to the batch. 
        The batch size is defined by _MAX_METRICS_PER_PUT_REQUEST.
        """
        metric_batch = []
        while len(metric_batch) < self._MAX_METRICS_PER_PUT_REQUEST and self.metric_map:
            key, metric = self.metric_map.popitem()
            metric_batch.append(metric)
        return metric_batch
