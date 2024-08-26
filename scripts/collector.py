#!/usr/bin/python3
from samm.config import Config
from samm.otlpattempt import start_exporter, collecting
import logging
import sys
import pika
import json

logging.basicConfig(stream=sys.stderr)
log = logging.getLogger(__name__)
config = None
attempt_dict = {}


def start_collector():
	start_exporter(config, attempt_dict, external_scheduler=True)
	_mq_server = config.get("mq.server", default='mq')
	_mq_queue_name = config.get("mq.queue_name", default="samm_attempts")
	_mq_queue_ttl = config.get("mq.queue_ttl", default=60000)
	connection = pika.BlockingConnection(pika.ConnectionParameters(host=_mq_server))
	channel = connection.channel()

	channel.queue_declare(queue=_mq_queue_name,
		arguments={'x-message-ttl' : _mq_queue_ttl}
	)

	def callback(ch, method, properties, body):
		if collecting:
			log.info(f" [x] Rejected message {body} {method.delivery_tag}")
			ch.basic_reject(delivery_tag = method.delivery_tag)
			return
		key = json.loads(body)
		attempt_dict[key].collect()
		log.debug(f" [x] Received {body} {method.delivery_tag}")
		ch.basic_ack(delivery_tag = method.delivery_tag)

	channel.basic_consume(queue=_mq_queue_name, on_message_callback=callback, auto_ack=False)

	log.info(' [*] Waiting for messages. To exit press CTRL+C')
	try:
		channel.start_consuming()
	except KeyboardInterrupt:
		log.info(' [*] Consumer shutdown')

if __name__ == "__main__":
	if len(sys.argv) != 2:
		raise TypeError("Usage: {sys.argv[0]} <config file>")
	config_file = sys.argv[1]
	config = Config(config_file)
	config.reload()
	log.setLevel(config.get("debug"))
	start_collector()
