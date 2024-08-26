from .attempt import Attempt
from samm.config import Config
from samm.utils import FilterFunction
import math
import logging
from opentelemetry import metrics
from opentelemetry.exporter.prometheus_remote_write import (
	PrometheusRemoteWriteMetricsExporter,
)
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

poll_interval = 5000
log = logging.getLogger(__name__)
collecting=False

class OTLPAttempt(Attempt):
	def __init__(self, *args, external_scheduler=False, **kwargs):
		super(OTLPAttempt, self).__init__(*args, **kwargs)
		self._external_scheduler = external_scheduler
		meter = metrics.get_meter(f"{self.name}")
		self._external_scheduler = external_scheduler
		if self._external_scheduler:
			self.schedule(math.inf)
		else:
			self.schedule(0)
		self._pending_metrics = []

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
		self.schedule(0)

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
		global collecting
		observations = []

		if len(self._pending_metrics) == 0:
			if not self.due():
				collecting = False
				return []
			if self._external_scheduler:
				self.schedule(math.inf)
			else:
				self.schedule_next()
			log.debug(f"Importing metrics from {self.name}")
			collecting = True
			self._cache = list(self.iterator)
			self._pending_metrics = set(self.check.metrics)

		for metric_data in self._cache:

			try:
				metric_tags = self.create_metric_tags(metric_data)
				value = self.get_metric_value(metric_data, metric_name)
				o = Observation(int(value), metric_tags)
				observations.append(o)

			except Exception as e:
				log.error("An error occurred processing %s.instance_metric_data. %s", self.name, e)
				log.exception(e)

		log.debug("Exported attempt %s.%s %d observations." % (self.name, metric_name, len(observations)))
		self._pending_metrics.remove(metric_name)
		return observations

def start_exporter(config, attempt_dict, external_scheduler=False):
	if not isinstance(config, Config):
		raise TypeError("Config has not been initialized")
	log.setLevel(config.get("debug"))

	instance_metric_data = {}
	for _, instance in config.get("instances").items():
		if not instance.register:
			continue
		for check_name in instance.checks:
			a = OTLPAttempt(config, 
					instance.name, 
					check_name, 
					instance_metric_data, 
					external_scheduler=external_scheduler
					)
			_ = attempt_dict.setdefault(a.name, a)

	_exporter_url = config.get("resources.prometheus_remote_write.url")
	_org_id = config.get("resources.prometheus_remote_write.org_id")
	if _exporter_url is None:
		raise TypeError("Parameter prometheus_remote_write in resources file is not defined")
	exporter = PrometheusRemoteWriteMetricsExporter(
		endpoint=_exporter_url,
		headers={
			'X-Scope-OrgID': _org_id
		},
	)
	reader = PeriodicExportingMetricReader(exporter, poll_interval)
	provider = MeterProvider(metric_readers=[reader])
	metrics.set_meter_provider(provider)
