from .config import Config
from .attempt import Attempt
import pika
from pika.adapters.select_connection import IOLoop
from .objecttype.instance import INSTANCE_UP, INSTANCE_DOWN, INSTANCE_PENDING
import json
import time
import logging
import sys
import math

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
		self._loop_sleep_s = self._config.get("loop_sleep_s", default=5)
		self._mq_server = self._config.get("mq.server", default='mq')
		self._mq_queue_orders = self._config.get("mq.queue_orders", default="samm_orders")
		self._mq_queue_reports = self._config.get("mq.queue_reports", default="samm_reports")
		self._mq_queue_ttl = self._config.get("mq.queue_ttl", default=60000)
		self._pending_retry = self._config.get("pending_retry", default=60)
		self.channel = None

	def init_attempts(self):
		self.attempt_dict = {}
		for instance_name in self._config.get("instances", default={}):
			log.debug("initializing %s" % instance_name)
			instance = self._config.get(("instances", instance_name))
			instance_metric_data = {}
			if instance.register:
				for check_name in instance.checks:
					try:
						a = Attempt(self._config, instance_name, check_name, instance_metric_data,
							pending_retry=self._pending_retry)
						if a.check.name == a.instance.up_check_name or a.instance.check_if_down:
							a.schedule(0)
						else:
							a.schedule(math.inf)
						_ = self.attempt_dict.setdefault(a.name, a)
					except Exception as e:
						log.exception("Unable to create attempt for %s-%s. %s", instance_name, check_name, str(e))

	def on_open(self, connection):
		log.debug("Connection opened.")
		connection.channel(on_open_callback=self.on_channel_open)

	def on_channel_open(self, channel):
		log.debug("Channel opened.")
		self.channel = channel

		def reports_callback(ch, method, properties, body):
			report = json.loads(body)
			if "type" not in report:
				raise Exception(f"Invalid report. Missing 'type'. {body}")
			report_type = report.pop('type')
			if report_type == 'up_check':
				report_up(report)
			elif report_type == 'done':
				report_done(report)
			else:
				log.warning(f"Unknown report type {report_type}. Data={report}")
			ch.basic_ack(delivery_tag = method.delivery_tag)

		def report_up(data):
			try:
				attempt_name = data['attempt_name']
				value = int(data['value'])
			except Exception as e:
				log.error(f"Invalid input from collector {data}")
				log.exception(e)
				return
			attempt = self.attempt_dict.get(attempt_name)
			if attempt is None:
				log.error(f"Attempt {attempt_name} is not defined")
				return
			if value == 0 and attempt.instance.is_alive == INSTANCE_UP:
				attempt.instance.is_alive = INSTANCE_DOWN
				for check_name in attempt.instance.checks:
					attempt = self.attempt_dict.get(f"{attempt.instance.name}.{check_name}")
					if attempt is not None:
						if attempt.instance.up_check_name == attempt.check.name:
							continue
						attempt.schedule(math.inf)
			elif value == 1 and attempt.instance.is_alive != INSTANCE_UP:
				attempt.instance.is_alive = INSTANCE_UP
				for check_name in attempt.instance.checks:
					attempt = self.attempt_dict.get(f"{attempt.instance.name}.{check_name}")
					if attempt is not None:
						if attempt.instance.up_check_name == attempt.check.name:
							continue
						attempt.schedule(0)
			log.debug(" [x] Received instance_up(%s)" % (str(data)))

		def report_done(data):
			log.debug(" [x] Received done(%s)'" % (str(data)))

		channel.queue_declare(queue=self._mq_queue_orders,
			arguments={'x-message-ttl' : self._mq_queue_ttl})

		channel.queue_declare(queue=self._mq_queue_reports,
			arguments={'x-message-ttl' : self._mq_queue_ttl})


		channel.basic_consume(queue=self._mq_queue_reports, on_message_callback=reports_callback, auto_ack=False)

	def order_attempt(self, attempt):
		if not attempt.due():
			return
		instance = attempt.instance
		check = attempt.check

		if not instance.check_if_down and \
				check.name != instance.up_check_name:
			if instance.is_alive == INSTANCE_DOWN:
				log.debug(f"Instance {instance.name} is DOWN skipping {attempt.name}")
				attempt.schedule_next()
				return
			elif instance.is_alive == INSTANCE_PENDING:
				log.debug(f"Instance {instance.name} is PENDING skipping {attempt.name}")
				attempt.schedule(attempt.pending_retry)
				return
		self.channel.basic_publish(exchange='',
			routing_key=self._mq_queue_orders,
			body=json.dumps({
				"type": "collect",
				"config_id": str(self._config._config_id),
				"attempt_name": attempt.name
				}))
		attempt.schedule_next()
		log.debug(" [x] Queued collect attempt(%s)'" % (attempt.name))

	def process_loop(self):
		if len(self.attempt_dict.keys()) < 1:
			raise TypeError("No attempts were defined.")

		connection = pika.SelectConnection(
			pika.ConnectionParameters(host=self._mq_server), 
			on_open_callback=self.on_open)


		try:
			loop_sleep_s = 1
			while self._keep_running:
				_ = connection.ioloop.call_later(loop_sleep_s, connection.ioloop.stop)
				connection.ioloop.start()
				while self.channel is None:
					log.debug("MQ not ready. Waiting.")
					time.sleep(1)
				for _, attempt in self.attempt_dict.items():
						self.order_attempt(attempt)
				loop_sleep_s = self._loop_sleep_s

		except KeyboardInterrupt:
			pass
		connection.close()

	def run(self):
		self.reload_config()
		self.init_attempts()
		self.process_loop()

