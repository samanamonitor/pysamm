from .objecttype.instance import INSTANCE_UP, INSTANCE_DOWN, INSTANCE_PENDING
from .utils import FilterFunction
from .config import Config
from .attempt import Attempt, log as attempt_log
import math
import logging
import time
from opentelemetry import metrics
from opentelemetry.exporter.prometheus_remote_write import (
	PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

log = logging.getLogger(__name__)

class OTLPAttempt(Attempt):
	def __init__(self, *args, external_scheduler=False, up_check_callback=None, done_callback=None, collector=None, **kwargs):
		self._collector = collector
		self._external_scheduler = external_scheduler
		self._pending_metrics = []
		self.up_check_callback = up_check_callback
		self.done_callback = done_callback
		self.collecting = False

		super(OTLPAttempt, self).__init__(*args, **kwargs)
		meter = metrics.get_meter(f"{self.name}")
		if self._external_scheduler:
			self.schedule(math.inf)
		else:
			self.schedule(0)

		# Info observable counters
		def info_callback(metric_tags, options):
			if not self.due():
				return []
			log.debug(f"   -- Sending info {self.name}.")
			return [Observation(1, metric_tags)]

		callback_func=lambda x, metric_tags=self.base_tags: \
			info_callback(metric_tags, x)
		description = f"This is an info counter for {self.name}"
		meter.create_observable_counter(
			f"{self.check.name}_info",
			callbacks=[callback_func],
			description=description)

		# UP observable counter
		if self.check.name == self.instance.up_check_name:
			callback_func=lambda x, metric_name="up": \
				self.observable_callback(metric_name, x)
			description = "Instance reachable"
			meter.create_observable_counter(
				f"up",
				callbacks=[callback_func],
				description=description)

		# All other observable counters
		for metric_name in self.check.metrics:
			name = f"{self.check.name}_{metric_name.lower()}"
			callback_func=lambda x, metric_name=metric_name: \
				self.observable_callback(metric_name, x)
			description = f"This is a counter for {self.name}.{metric_name}"
			meter.create_observable_counter(
				name,
				callbacks=[callback_func],
				description=description)
			log.debug(f"Created counter for {self.name}.{metric_name}")

	def collect(self):
		if self._collector is None:
			log.debug(f"Collector not defined")
			return False
		if self._collector.collecting:
			log.debug(f"This collector is busy collecting. Rejecting request.")
			return False
		if self.next_run - time.time() < 0:
			log.debug(f"Attempt {self.name} is already due or collecting.")
			return False
		self.collecting = True
		self._collector.collecting = True
		self.schedule(0)
		return True

	def create_metric_tags(self, metric_data):
		metric_tags = self.base_tags.copy()
		for tag_property in self.tag_properties:
			if isinstance(tag_property, str):
				property_name = tag_property
				transform_name = "str"
			elif isinstance(tag_property, dict):
				property_name = tag_property.get('property', "none")
				transform_name = tag_property.get("transform", "str")

			key = property_name.lower()
			transform = getattr(FilterFunction, transform_name, str)
			value = transform(metric_data.get(property_name, "none"))
			metric_tags[key] = value
		return metric_tags

	def get_metric_value(self, metric_data, metric_name):
		value_mapping = self.value_mappings.get(metric_name, {})
		value = metric_data.get(metric_name, -1)
		if isinstance(value, str) and value_mapping:
			default_mapping = value_mapping.get("*", -1)
			value = value_mapping.get(value, default_mapping)
		if not isinstance(value, (int, float)):
			value = -1
		return value

	def observable_callback(self, metric_name, options):
		observations = []

		if len(self._pending_metrics) == 0:
			if not self.due():
				return []
			if self._external_scheduler:
				self.schedule(math.inf)
			else:
				self.schedule_next()
			log.debug(f"Importing metrics from {self.name}")
			try:
				self._cache = list(self.iterator)
				self._pending_metrics = set(self.check.metrics)
				if self.instance.up_check_name == self.check.name:
					self._pending_metrics.add("up")
					for i in self._cache:
						i["up"] = i[self.instance.up_metric_name]
			except Exception as e:
				log.error("An error occurred processing %s.instance_metric_data. %s", self.name, e)
				#log.exception(e)
				if self.collecting:
					self.collecting = False
					self._collector.collecting = False
					if callable(self.done_callback):
						self.done_callback(self.name)
				return []

		for metric_data in self._cache:

			try:
				metric_tags = self.create_metric_tags(metric_data)
				value = self.get_metric_value(metric_data, metric_name)
				o = Observation(int(value), metric_tags)
				observations.append(o)

			except Exception as e:
				log.error("An error occurred processing %s.instance_metric_data. %s", self.name, e)
				#log.exception(e)

		if self.check.name == self.instance.up_check_name and \
				metric_name == self.instance.up_metric_name:
			value = self._cache[0].get(metric_name, 0)
			if callable(self.up_check_callback):
				self.up_check_callback(self.name, value)
			if value == 0:
				self.instance.is_alive = INSTANCE_DOWN
			else:
				self.instance.is_alive = INSTANCE_UP

		log.debug("Exported attempt %s.%s %d observations." % (self.name, metric_name, len(observations)))
		self._pending_metrics.remove(metric_name)
		if len(self._pending_metrics) == 0 and self.collecting:
			self.collecting = False
			self._collector.collecting = False
			if callable(self.done_callback):
				self.done_callback(self.name)
		return observations

def start_exporter(collector, up_check_callback=None, done_callback=None, external_scheduler=False):
	config = collector.config
	attempt_dict = collector.attempt_dict
	#log.setLevel(config.get("debug"))
	#attempt_log.setLevel(config.get("debug"))

	instance_metric_data = {}
	for _, instance in config.get("instances").items():
		if not instance.register:
			continue
		meter = metrics.get_meter(instance.name)


		metric_tags = {}
		metric_tags.update(config.get(("tags"), default={}, resolve_vars=True))
		metric_tags.update(config.get(("instances", instance.name, "tags"), default={}, resolve_vars=True))
		metric_tags['instance'] = instance.name

		def info_callback(metric_tags, options):
			log.debug("host_info %s" % metric_tags)
			return [Observation(1, metric_tags)]

		callback_func=lambda x, metric_tags=metric_tags: \
			info_callback(metric_tags, x)
		description = f"This is a counter for {instance.name}"
		meter.create_observable_counter(
			"instance_info",
			callbacks=[callback_func],
			description=description)
		for check_name in instance.checks:
			a = OTLPAttempt(config, 
					instance.name, 
					check_name, 
					instance_metric_data, 
					external_scheduler=external_scheduler,
					up_check_callback=up_check_callback,
					done_callback=done_callback,
					collector=collector
					)
			_ = attempt_dict.setdefault(a.name, a)

	_exporter_url = config.get("resources.prometheus_remote_write.url")
	_org_id = config.get("resources.prometheus_remote_write.org_id")
	_export_interval = config.get("resources.prometheus_remote_write.export_interval", default=5000)
	if _exporter_url is None:
		raise TypeError("Parameter prometheus_remote_write in resources file is not defined")
	exporter = PrometheusRemoteWriteMetricsExporter(
		endpoint=_exporter_url,
		headers={
			'X-Scope-OrgID': _org_id
		},
	)
	reader = PeriodicExportingMetricReader(exporter, _export_interval)
	provider = MeterProvider(metric_readers=[reader])
	metrics.set_meter_provider(provider)

#### This code will replace the previous code eventually
class OTLPExporter:
	def __init__(self, collector, up_check_callback=None, done_callback=None, external_scheduler=False):
		self.collector = collector
		self.config = self.collector.config
		log.setLevel(config.get("debug"))
		#attempt_log.setLevel(config.get("debug"))
		self._exporter_url = config.get("resources.prometheus_remote_write.url")
		self._org_id = config.get("resources.prometheus_remote_write.org_id")
		self._export_interval = config.get("resources.prometheus_remote_write.export_interval", default=5000)
		self._up_check_callback = up_check_callback
		self._done_callback = done_callback
		self._external_scheduler = external_scheduler
		if self._exporter_url is None:
			raise TypeError("Parameter prometheus_remote_write in resources file is not defined")
		exporter = PrometheusRemoteWriteMetricsExporter(
			endpoint=self._exporter_url,
			headers={
				'X-Scope-OrgID': _org_id
			},
		)
		reader = PeriodicExportingMetricReader(exporter, self._export_interval)
		self._provider = MeterProvider(metric_readers=[reader])

	def start(self):
		metrics.set_meter_provider(self._provider)
		instance_metric_data = {}
		for _, instance in self.config.get("instances").items():
			if not instance.register:
				continue
			for check_name in instance.checks:

				a = OTLPAttempt(config, 
						instance.name, 
						check_name, 
						instance_metric_data, 
						external_scheduler=self._external_scheduler,
						up_check_callback=self._up_check_callback,
						done_callback=self._done_callback,
						collector=self.collector
						)
				if a._external_scheduler:
					a.schedule(math.inf)
				else:
					a.schedule(0)
				_ = self.collector.attempt_dict.setdefault(a.name, a)

				meter = metrics.get_meter(f"{a.name}")
				# Info observable counters
				def info_callback(attempt, options):
					if not attempt.due():
						return []
					log.debug(f"   -- Sending info {attempt.name}.")
					return [Observation(1, attempt.base_tags)]

				callback_func=lambda x, attempt=a: \
					info_callback(attempt, x)
				description = f"This is an info counter for {a.name}"
				meter.create_observable_counter(
					f"{a.check.name}_info",
					callbacks=[callback_func],
					description=description)

				# UP observable counter
				if a.check.name == a.instance.up_check_name:
					callback_func=lambda x, metric_name="up": \
						a.observable_callback(metric_name, x)
					description = "Instance reachable"
					meter.create_observable_counter(
						f"up",
						callbacks=[callback_func],
						description=description)

				# All other observable counters
				for metric_name in a.check.metrics:
					name = f"{a.check.name}_{metric_name.lower()}"
					callback_func=lambda x, metric_name=metric_name: \
						a.observable_callback(metric_name, x)
					description = f"This is a counter for {a.name}.{metric_name}"
					meter.create_observable_counter(
						name,
						callbacks=[callback_func],
						description=description)
					log.debug(f"Created counter for {a.name}.{metric_name}")

