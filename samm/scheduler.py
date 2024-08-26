from .config import Config
from .attempt import Attempt
import pika
import json
import time
import logging

log = logging.getLogger(__name__)

class Scheduler:
	def __init__(self, config_path):
		self._config_path = config_path
		self._keep_running = True

	def reload_config(self):
		self._config = Config(self._config_path)
		self._config.reload()
		self._debug_level = self._config.get("debug", default="INFO")
		log.setLevel(self._debug_level)
		logging.basicConfig(stream=sys.stderr)
		self._loop_sleep = self._config.get("loop_sleep", default=5)
		self._mq_server = self._config.get("mq.server", default='mq')
		self._mq_queue_name = self._config.get("mq.queue_name", default="samm_attempts")
		self._mq_queue_ttl = self._config.get("mq.queue_ttl", default=60000)
		self._pending_retry = self._config.get("pending_retry", default=60)

	def init_attempts(self):
		self.attempt_list = []
		for instance_name in self._config.get("instances", default={}):
			log.debug("initializing %s" % instance_name)
			instance = self._config.get(("instances", instance_name))
			instance_metric_data = {}
			if instance.register:
				for check_name in instance.checks:
					try:
						a = Attempt(self._config, instance_name, check_name, instance_metric_data,
							pending_retry=self._pending_retry)
						log.debug("Created attempt %s:%s", instance_name, check_name)
						a.schedule(0)
						self.attempt_list += [ a ]
					except Exception as e:
						log.exception("Unable to create attempt for %s-%s. %s", instance_name, check_name, str(e))

	def process_loop(self):
		connection = pika.BlockingConnection(
			pika.ConnectionParameters(host=self._mq_server))
		self.channel = connection.channel()
		self.channel.queue_declare(queue=self._mq_queue_name,
			arguments={'x-message-ttl' : self._mq_queue_ttl})
		try:
			while self._keep_running:
				due_attempts = []
				for a in self.attempt_list:
					if a.due():
						due_attempts += [a]
						a.schedule_next()
				self.order_attempts(due_attempts)
				time.sleep(self._loop_sleep)
		except KeyboardInterrupt:
			pass
		connection.close()

	def order_attempts(self, attempt_list):
		if len(attempt_list) < 1:
			return
		log.debug("mq_server=%s, mq_routing_key=%s, mq_queue_name=%s" % 
			(self._mq_server, self._mq_queue_name, self._mq_queue_name))
		for attempt in attempt_list:
			self.channel.basic_publish(exchange='', 
				routing_key=self._mq_queue_name, 
				body=json.dumps(attempt.name))
			log.debug(" [x] Queued attempt(%s)'" % (attempt.name))

	def run(self):
		scheduler.reload_config()
		scheduler.init_attempts()
		scheduler.process_loop()

