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
		self._mq_queue_name = self.config.get("mq.queue_name", default="samm_attempts")
		self._mq_queue_report_up = self.config.get("mq.queue_report_up", default="samm_report_up")
		self._mq_queue_report_done = self.config.get("mq.queue_report_done", default="samm_report_done")
		self._mq_queue_ttl = self.config.get("mq.queue_ttl", default=60000)
		self.attempt_dict = {}
		self.collecting = False
		self.connection = None

	def on_open(self, connection):
		connection.channel(on_open_callback=self.on_channel_open)

	def on_channel_open(self, channel):

		def message_callback(ch, method, properties, body):
			key = json.loads(body)
			log.debug(f" [x] Received {body} {method.delivery_tag}")
			if not self.attempt_dict[key].collect():
				log.debug(f" [x] Rejected message {body} {method.delivery_tag}")
				ch.basic_reject(delivery_tag = method.delivery_tag)
				return
			log.debug(f" [x] Accepted {body} {method.delivery_tag}")
			ch.basic_ack(delivery_tag = method.delivery_tag)
			self.connection.ioloop.add_callback(self.connection.ioloop.stop)

		def up_check_callback(instance_name, value):
			channel.basic_publish(exchange='', 
					routing_key=self._mq_queue_report_up, 
					body=json.dumps({
						"attempt_name": instance_name,
						"value": value
						}))
			log.debug(" [x] Queued instance_up(%s=%s)'" % (instance_name, str(value)))

		def done_callback(data):
			channel.basic_publish(exchange='', 
					routing_key=self._mq_queue_report_done, 
					body=json.dumps({
						"attempt_name": data
						}))
			log.debug(f" [v] Collecting done by {str(data)}")

		channel.queue_declare(queue=self._mq_queue_name,
			arguments={'x-message-ttl' : self._mq_queue_ttl})

		channel.queue_declare(queue=self._mq_queue_report_up,
			arguments={'x-message-ttl' : self._mq_queue_ttl})

		channel.queue_declare(queue=self._mq_queue_report_done,
			arguments={'x-message-ttl' : self._mq_queue_ttl})

		channel.basic_consume(queue=self._mq_queue_name, on_message_callback=message_callback, auto_ack=False)
		start_exporter(self, up_check_callback=up_check_callback, done_callback=done_callback, external_scheduler=True)

	def run(self):
		self.connection = pika.SelectConnection(
			pika.ConnectionParameters(host=self._mq_server), 
			on_open_callback=self.on_open)
		log.info(' [*] Waiting for messages. To exit press CTRL+C')
		try:
			while True:
				if not self.collecting:
					self.connection.ioloop.start()
				time.sleep(0.5)
		except KeyboardInterrupt:
			connection.close()
			log.info(' [*] Consumer shutdown')

