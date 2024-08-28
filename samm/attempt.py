from threading import Thread
from .metric import InstanceMetric
from .utils import FilterFunction
import time
import logging
import math
from random import Random
from .objecttype.instance import INSTANCE_UP, INSTANCE_DOWN, INSTANCE_PENDING

log = logging.getLogger(__name__)

class Attempt:
	def __init__(self, config, instance_name, check_name, instance_metric_data, pending_retry=60):
		self.config = config

		self.instance=config.get(("instances", instance_name))
		if self.instance is None:
			raise KeyError("Instance not found", instance_name)
		if check_name not in self.instance.checks:
			raise KeyError("Check not found in instance", instance_name, check_name)
		self.check=config.get(("checks", check_name))
		if self.check is None:
			raise TypeError("Check not found", check_name)
		self.command = config.get(("commands", self.check.command))
		if self.command is None:
			raise TypeError("Command not found", self.check.command)

		self.next_run = 0
		self.alias = self.check.get("alias", default=self.check.name)
		self.metrics = self.check.metrics

		self.thread = None
		self.tag_properties = config.get(("checks", check_name, "tag_properties"), \
					resolve_vars=True, default=[])
		self.base_tags = {}
		self.base_tags.update(config.get(("tags"), default={}, resolve_vars=True))
		self.base_tags.update(config.get(("instances", instance_name, "tags"), default={}, resolve_vars=True))
		self.base_tags.update(config.get(("checks", check_name, "tags"), default={}, resolve_vars=True))
		self.base_tags['instance'] = self.instance.name
		self.value_mappings = self.check.get('value_mappings', {})
		self.instance_metric_data = instance_metric_data
		log.debug("Attempt created. %s:%s", instance_name, check_name)
		self.rand = Random(time.time())
		self.pending_retry = pending_retry

	@property
	def name(self):
		return f"{self.instance.name}.{self.check.name}"

	def due(self):
		if self.next_run == 0:
			return False
		return time.time() > self.next_run

	def process(self):
		if not self.due():
			return False
		log.debug("Attempt %s:%s due for execution.", self.instance.name, self.check.name)
		if self.thread is not None and self.thread.is_alive():
			log.warning("Last attempt is still running. (%s:%s)", self.instance.name, self.check.name)
			return False
		if self.instance.check_if_down is False and self.check.name != self.instance.up_check_name:
			if self.instance.is_alive == INSTANCE_DOWN:
				log.debug("Instance is down. Skipping attempt %s:%s.", \
					self.instance.name, self.check.name)
				self.schedule_next()
				return False
			elif self.instance.is_alive == INSTANCE_PENDING:
				log.debug("Instance is pending. Skipping attempt %s:%s for %d seconds.", \
					self.instance.name, self.check.name, self.pending_retry)
				self.schedule(self.pending_retry)
				return False

		self.thread = Thread(target=self.run)
		self.thread.start()
		return True

	@property
	def iterator(self):
		command_args=self.config.get(("commands", self.command.name, "args"),
			instance_name=self.instance.name,
			check_name=self.check.name,
			resolve_vars=True,
			default={})
		#command_args.setdefault('tags', {}).update(self.base_tags)
		return self.config.run_module(self.command.type, **command_args)


	def run(self, schedule_next=True):
		self.next_run = 0

		try:
			metric_received = 0
			for metric_data in self.iterator:
				metric_received = 1
				metric_tags = self.base_tags.copy()
				for tag_property in self.tag_properties:
					if isinstance(tag_property, str):
						property_name = tag_property
						transform_name = "str"
					elif isinstance(tag_property, dict):
						property_name = tag_property.get('property', "none")
						transform_name = tag_property.get("transform", "str")

					key = property_name.lower()
					transform = getattr(FilterFunction, transform_name, lambda x: str(x))
					value = transform(metric_data.get(property_name, "none"))
					metric_tags[key] = value

				try:
					for metric_name in self.metrics:
						if self.check.name == self.instance.up_check_name and \
								metric_name == self.instance.up_metric_name:
							value = metric_data.get(metric_name, 0)
							if value == 0:
								self.instance.is_alive = INSTANCE_DOWN
							else:
								self.instance.is_alive = INSTANCE_UP
							im = InstanceMetric("up", value, metric_tags, \
								stale_timeout=self.instance.stale_timeout)

						else:
							value = metric_data.get(metric_name, -1)
							im = InstanceMetric(metric_name.lower(), value, metric_tags, \
								prefix=self.alias.lower(), stale_timeout=self.check.stale_timeout,
								value_mapping=self.value_mappings.get(metric_name))

						self.instance_metric_data[im.key] = im

				except Exception as e:
					log.error("An error occurred processing (%s:%s).metrics\nmetric_data=%s. %s",
						self.instance.name, self.check.name, metric_data, e)

		except Exception as e:
			log.error("An error occurred processing (%s:%s).instance_metric_data. %s", self.instance.name, self.check.name, e)
			pass

		if schedule_next:
			self.schedule_next()

		return True

	def schedule_next(self):
		self.schedule(self.check.get("check_interval"))

	def schedule(self, seconds):
		if self.rand is not None and seconds > 0:
			r = self.rand.uniform(-8, 8)
		else:
			r = 0
		self.next_run = time.time() + seconds + r
		log.debug("Scheduling %s in %ss", self.name, str(int(self.next_run - time.time())))

	def __repr__(self):
		run_in_seconds = self.next_run - time.time()
		if run_in_seconds == math.inf:
			run_in_seconds = "never"
		elif run_in_seconds < 0:
			run_in_seconds = "due"
		else:
			run_in_seconds = "%ds" % int(run_in_seconds)
		return f"<{self.__class__.__name__} {self.name} next_run_in={run_in_seconds}>"
