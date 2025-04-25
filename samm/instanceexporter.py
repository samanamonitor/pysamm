from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from threading import Thread
import logging

log = logging.getLogger(__name__)

class MetricHttpRequestHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		self.protocol_version = 'HTTP/1.1'
		if self.path == "/metrics":
			return self.metrics()
		self.send_error(404, message="Not Found")

	def metrics(self):
		data = b""
		for metric_name, metric in self.server.metric_data.items():
			data += str(metric).encode('ascii')

		self.send_response_only(200)
		self.send_header('Server', self.version_string())
		self.send_header('Date', self.date_time_string())
		self.send_header('Content-Type', 'text/plain')
		self.send_header('Content-Length', str(len(data)))
		self.send_header('Connection', 'close')
		self.end_headers()
		self.wfile.write(data)
		log.info(f"Requested metrics for instance={self.server.metric_data.name} " +
			f"from={self.client_address[0]}:{self.client_address[1]}")

class InstanceExporter(dict):
	def __init__(self, instance_name, port):
		self.name = instance_name
		self.myport = port
		self.myip = socket.gethostbyname(socket.gethostname())
		server_address = ('', port)

		self.httpd = HTTPServer(server_address, MetricHttpRequestHandler)
		self.httpd.metric_data = self
		self.httpdthread = Thread(target=self.httpd.serve_forever)
		self.httpdthread.start()


	def sd_config(self):
		return {
			"targets": [ 
				f"{self.myip}:{self.myport}"
			],
			"labels": {
				"instance": self.name
			}
		}