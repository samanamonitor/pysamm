from threading import Thread
from .metric import InstanceMetric
import time
import logging
from random import Random
from .objecttype.instance import INSTANCE_UP, INSTANCE_DOWN, INSTANCE_PENDING

log = logging.getLogger(__name__)

class Attempt:
	def __init__(self, config, instance_name, check_name, instance_metric_data, pending_retry=60):
		self.check=config.get(("checks", check_name))
		if self.check is None:
			raise TypeError("Check %s not found" % check_name)
		self.config = config
		self.instance=config.get(("instances", instance_name))
		self.next_run = 0
		self.instance_name=instance_name
		self.check_name = check_name
		self.alias = self.check.get('alias', check_name)
		self.metrics = config.get(("checks", check_name, "metrics"))
		self.command="commands", config.get(("checks", check_name, "command"), \
			resolve_vars=True)
		self.module_name=config.get(self.command + ("type",), 
			instance_name=instance_name, check_name=check_name, resolve_vars=True)

		self.thread = None
		self.instance_stale_timeout = config.get(("instances", instance_name, "stale_timeout"))
		self.check_stale_timeout = config.get(("checks", check_name, "stale_timeout"))
		self.tag_properties = config.get(("checks", check_name, "tag_properties"), \
					resolve_vars=True, default=[])
		self.base_tags = {}
		self.base_tags.update(config.get(("tags"), default={}))
		self.base_tags.update(config.get(("instances", instance_name, "tags"), default={}))
		self.base_tags.update(config.get(("checks", check_name, "tags"), default={}))
		self.base_tags['instance'] = self.instance_name
		self.value_mappings = self.check.get('value_mappings', {})
		self.instance_metric_data = instance_metric_data
		log.debug("Attempt created. %s:%s", instance_name, check_name)
		self.rand = Random(time.time())
		self.pending_retry = pending_retry

	def due(self):
		if self.next_run == 0:
			return False
		return time.time() > self.next_run

	def process(self):
		if not self.due():
			return False
		log.debug("Attempt %s:%s due for execution.", self.instance_name, self.check_name)
		if self.thread is not None and self.thread.is_alive():
			log.warning("Last attempt is still running. (%s:%s)", self.instance_name, self.check_name)
			return False
		if self.instance.check_if_down is False and self.check_name != self.instance.up_check_name:
			if self.instance.is_alive == INSTANCE_DOWN:
				log.info("Instance is down. Skipping attempt %s:%s.", \
					self.instance_name, self.check_name)
				self.schedule_next()
			elif self.instance.is_alive == INSTANCE_PENDING:
				log.info("Instance is pending. Skipping attempt %s:%s for %d seconds.", \
					self.instance_name, self.check_name, self.pending_retry)
				self.schedule(self.pending_retry)
			return False

		self.thread = Thread(target=self.run)
		self.thread.start()
		return True

	def run(self, schedule_next=True):
		self.next_run = 0

		command_args=self.config.get(self.command + ("args",),
			instance_name=self.instance.name, check_name=self.check.name, resolve_vars=True)
		#command_args.setdefault('tags', {}).update(self.base_tags)
		data = self.config.run_module(self.module_name, **command_args)

		try:
			metric_received = 0
			for metric_data in data:
				metric_received = 1
				metric_tags = self.base_tags.copy()
				for tag_property in self.tag_properties:
					key = tag_property.lower()
					value = str(metric_data.get(tag_property, "none")).lower()
					metric_tags.update({ key: value })

				try:
					for metric_name in self.metrics:
						if self.check_name == self.instance.up_check_name and \
								metric_name == self.instance.up_metric_name:
							value = metric_data.get(metric_name, 0)
							if value == 0:
								self.instance.is_alive = INSTANCE_DOWN
							else:
								self.instance.is_alive = INSTANCE_UP
							im = InstanceMetric("up", value, metric_tags, \
								stale_timeout=self.instance_stale_timeout)

						else:
							value = metric_data.get(metric_name, -1)
							im = InstanceMetric(metric_name.lower(), value, metric_tags, \
								prefix=self.alias.lower(), stale_timeout=self.check_stale_timeout,
								value_mapping=self.value_mappings.get(metric_name))

						self.instance_metric_data[im.key] = im

				except Exception as e:
					log.exception("An error occurred processing (%s:%s).metrics\nmetric_data=%s. %s",
						self.instance_name, self.check_name, metric_data, e)

		except Exception as e:
			log.exception("An error occurred processing (%s:%s).instance_metric_data. %s", self.instance_name, self.check_name, e)
			pass

		if schedule_next:
			self.schedule_next()

		return True

	def schedule_next(self):
		self.schedule(self.check.get("check_interval"))

	def schedule(self, seconds):
		if self.rand is not None:
			r = self.rand.uniform(-8, 8)
		else:
			r = 0
		self.next_run = time.time() + seconds + r
		log.debug("Scheduling %s:%s to %s", self.instance_name, self.check_name, str(self.next_run))
