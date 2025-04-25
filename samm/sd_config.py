from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

log = logging.getLogger(__name__)

class SdConfigHttpRequestHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		self.protocol_version = 'HTTP/1.1'
		if self.path == "/sd_config":
			return self.sd_config()
		self.send_error(404, message="Not Found")

	def sd_config(self):
		data = json.dumps(
			[ x for _, x in self.server.sd_config.items()])

		self.send_response_only(200)
		self.send_header('Server', self.version_string())
		self.send_header('Date', self.date_time_string())
		self.send_header('Content-Type', 'application/json')
		self.send_header('Content-Length', str(len(data)))
		self.send_header('Connection', 'close')
		self.end_headers()
		self.wfile.write(data.encode('ascii'))
		log.info(f"Requested sd_config " +
			f"from={self.client_address[0]}:{self.client_address[1]}")
