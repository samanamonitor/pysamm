from .config import Config
from .otlpattempt import start_exporter
import logging
import pika
import json
import sys
import time

log = logging.getLogger(__name__)

class Collector:
	def __init__(self, config_file):
		self.config = Config(config_file)
		self.config.reload()
		log.setLevel(self.config.get("debug"))
		logging.basicConfig(stream=sys.stderr)
		self._mq_server = self.config.get("mq.server", default='mq')
		self._mq_queue_orders = self.config.get("mq.queue_orders", default="samm_orders")
		self._mq_queue_reports = self.config.get("mq.queue_reports", default="samm_reports")
		self._mq_queue_ttl = self.config.get("mq.queue_ttl", default=60000)
		self.attempt_dict = {}
		self.collecting = False
		self.connection = None
		self._delivery_tag = None
		self.collection_count = 0

	def on_open(self, connection):
		connection.channel(on_open_callback=self.on_channel_open)

	def on_open_error_callback(self, connection, err):
		log.exception(err)
		self.connection.close()
		sys.exit(1)

	def on_close_callback(self, connectin, err):
		log.exception(err)
		self.connection.close()
		sys.exit(0)

	def on_channel_open(self, channel):

		def message_callback(ch, method, properties, body):
			order = json.loads(body)
			if 'type' not in order:
				raise Exception(f"Invalid order. Missing 'type'. {body}")
			order_type = order.pop('type')
			config_id = order.pop('config_id', None)
			if config_id != str(self.config._config_id):
				log.warning(f"Version mismatch. scheduler_config_id={config_id} collector_config_id={self.config._config_id}")
				mismatch_action = self.config.get('config_version_mismatch_action', 'ignore')
				if mismatch_action == 'ignore':
					log.warning(f"Version mismatch. action=ignore")
				elif mismatch_action == 'exit':
					log.warning(f"Version mismatch. action=exit")
					sys.exit(0)
			log.debug(f" [x] Received {body} {method.delivery_tag}")
			if order_type == "collect":
				result = collect(order)
			if result:
				self._delivery_tag = method.delivery_tag
				log.debug(f" [x] Accepted {body} {method.delivery_tag}")
			else:
				ch.basic_reject(delivery_tag = method.delivery_tag)
				log.debug(f" [x] Rejected message {body} {method.delivery_tag}")

		def collect(order):
			try:
				attempt_name = order['attempt_name']
			except Exception as e:
				log.error(f"Invalid input from scheduler {data}")
				log.exception(e)
				return False

			return self.attempt_dict[attempt_name].collect()

		def up_check_callback(instance_name, value):
			channel.basic_publish(exchange='', 
					routing_key=self._mq_queue_reports,
					body=json.dumps({
						"type": "up_check",
						"attempt_name": instance_name,
						"value": value
						}))
			log.debug(" [x] Queued instance_up(%s=%s)'" % (instance_name, str(value)))

		def done_callback(data):
			channel.basic_ack(delivery_tag = self._delivery_tag)
			channel.basic_publish(exchange='', 
					routing_key=self._mq_queue_reports,
					body=json.dumps({
						"type": "done",
						"attempt_name": data
						}))
			log.debug(f" [v] Collecting done by {str(data)}")
			self.collection_count += 1


		channel.queue_declare(queue=self._mq_queue_orders,
			arguments={'x-message-ttl' : self._mq_queue_ttl})

		channel.queue_declare(queue=self._mq_queue_reports,
			arguments={'x-message-ttl' : self._mq_queue_ttl})

		channel.basic_qos(prefetch_count=1)
		channel.basic_consume(queue=self._mq_queue_orders, on_message_callback=message_callback, auto_ack=False)
		start_exporter(self, up_check_callback=up_check_callback, done_callback=done_callback, external_scheduler=True)

	def run(self):
		self.connection = pika.SelectConnection(
			pika.ConnectionParameters(host=self._mq_server), 
			on_open_callback=self.on_open, on_open_error_callback=self.on_open_error_callback, 
			on_close_callback=self.on_close_callback)
		log.info(' [*] Waiting for messages. To exit press CTRL+C')
		try:
			self.connection.ioloop.start()
		except KeyboardInterrupt:
			self.connection.close()
			log.info(' [*] Consumer shutdown')
		except Exception as e:
			log.exception(e)

