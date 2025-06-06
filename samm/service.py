from .config import Config
from .attempt import Attempt
from .metric import InstanceMetric
from time import sleep, process_time, time
import socket, select, os, signal, sys
import threading
import logging

log = logging.getLogger(__name__)

class Service:

	def __init__(self, config_file):
		self.running_config = None
		self.keep_running = False
		self.sock = None
		self.debug = 0
		self.config_path = ""
		self.config_file = ""
		self.keep_running = True
		self.reload_config = False
		self.stop_loop = True
		self.initial_spread = 1
		self.abs_config_file = os.path.abspath(config_file)
		self.attempt_list = []
		self.config_path, sep, self.config_file = config_file.rpartition("/")
		self.load_config()
		log.debug("Service startup. %d" % ( int(time()) ))
		self.keep_running = self.running_config._valid_config
		self.attempts_run_in_loop = 0
		self.loop_time = 0
		self.max_attempts_per_loop = self.running_config.get("max_attempts_per_loop", 1000)

		self.init_local_metrics()
		self.init_attempts()
		self.init_sock()
		signal.signal(signal.SIGHUP, self.signal_handler)
		signal.signal(signal.SIGINT, self.signal_handler)

	def init_local_metrics(self):
		self.startup_time = InstanceMetric("samm_startup_time", time(), self.tags)
		self.metric_count = InstanceMetric("samm_metric_count", 0, self.tags)
		self.host_count   = InstanceMetric("samm_host_count", 0, self.tags)
		self.scheduled_attempts = InstanceMetric("samm_scheduled_attempts_count", 0, self.tags)
		self.running_time = InstanceMetric("samm_running_time_seconds_count", 0, self.tags)
		self.metric_data_bytes = InstanceMetric("samm_metric_data_bytes", 0, self.tags)
		self.thread_count = InstanceMetric("samm_thread_count", 0, self.tags)
		self.pt = InstanceMetric("samm_process_time_seconds_count", 0, self.tags)
		self.metric_data = { 
			self.tags.get('instance', 'samm'): {
				self.startup_time.key: self.startup_time,
				self.metric_count.key: self.metric_count,
				self.host_count.key: self.host_count,
				self.scheduled_attempts.key: self.scheduled_attempts,
				self.running_time.key: self.running_time,
				self.pt.key: self.pt,
				self.metric_data_bytes.key: self.metric_data_bytes,
				self.thread_count.key: self.thread_count
			}
		}

	def load_config(self):
		self.running_config=Config(self.abs_config_file)
		self.running_config.reload()
		self._stale_timeout = self.running_config.get("stale_timeout", default=600)
		self.poll_time = self.running_config.get("poll_time", default=5)
		self.pending_retry = self.running_config.get("pending_retry", default=60)
		self.tags = self.running_config.get('service_tags', default={}).copy()
		self.tags.update(self.running_config.get('tags'))
		self.initial_spread = self.running_config.get("initial_spread", 1.0)

	def init_instance_attempts(self, instance):
		instance_name = instance.name
		instance_metric_data = self.metric_data.setdefault(instance.name, {})
		if instance.register:
			self.host_count.val(self.host_count.val() + 1)
			for check_name in instance.checks:
				try:
					a = Attempt(self.running_config, instance.name, check_name, instance_metric_data,
						pending_retry=self.pending_retry)
					log.debug("Created attempt %s:%s", instance.name, check_name)
					a.schedule(self.scheduled_attempts.val() * self.initial_spread)
					self.attempt_list += [ a ]
					self.scheduled_attempts.val(self.scheduled_attempts.val() + 1)
				except Exception as e:
					log.exception("Unable to create attempt for %s-%s. %s", instance.name, check_name, str(e))

	def init_attempts(self):
		self.attempt_list = []
		self.host_count.val(0)
		self.scheduled_attempts.val(0)
		for instance_name in self.running_config.get("instances", default={}):
			instance = self.running_config.get(("instances", instance_name))
			self.init_instance_attempts(instance)

	def discover(self):
		do=self.running_config.discover_objects()
		dobj=self.running_config.process_objects(do)
		for obj in dobj:
			self.init_instance_attempts(obj)

	def init_sock(self):
		self.sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		conf_sock_file = self.running_config.get("sock_file")
		if not os.path.isabs(self.running_config.get("sock_file")):
			sock_file = os.path.join(self.running_config.get('base_dir'), conf_sock_file)
		else:
			sock_file = conf_sock_file
		if os.path.exists(sock_file):
			os.unlink(sock_file)
		self.sock.bind(sock_file)
		os.chmod(sock_file, 0x0777)
		self.sock.listen(1)

	def process_attempts(self):
		self.attempts_run_in_loop = 0
		for attempt in self.attempt_list:
			try:
				if attempt.process():
					self.attempts_run_in_loop += 1
					log.debug("Running attempt alias=%s instance_name=%s check_name=%s.",
						attempt.alias, attempt.instance.name, attempt.check.name)
					if self.attempts_run_in_loop > self.max_attempts_per_loop:
						log.warning("Max number of attempts per loop reached. All other attempts will be tried in the next loop")
						return
			except Exception as e:
				log.exception("Got error from Attempt.run() : %s - instance=%s check=%s",
					str(e), attempt.instance.name, attempt.check.name)

	def process_loop(self):
		while self.keep_running:
			self.process_attempts()
			self.maintain_metric_data()
			self.process_prompt_request()
			self.discover()
			if self.reload_config:
				self.load_config()
				self.reload_config = False
				self.init_attempts()
		self.keep_running = True

	def maintain_metric_data(self):
		self.metric_data_bytes.val(sys.getsizeof(self.metric_data_bytes))
		self.running_time.val(time() - self.startup_time.val())
		current_pt = process_time()
		self.loop_time = current_pt - self.pt.val()
		self.pt.val(current_pt)
		self.thread_count.val(threading.active_count())
		mc = 0
		stale_list = []
		instance_name_list = list(self.metric_data.keys())
		for instance_name in instance_name_list:
			instance_metrics = self.metric_data.get(instance_name, None)
			if instance_metrics is None: continue
			metric_key_list = list(instance_metrics.keys())
			for metric_key in metric_key_list:
				metric = instance_metrics.get(metric_key, None)
				if metric is None: continue
				if metric.is_stale():
					stale_list += [(instance_name, metric_key)]
					continue
				mc += 1
		for s in stale_list:
			self.metric_data[s[0]].pop(s[1])
			log.debug("Cleanup metric %s.%s", *s)

		self.metric_count.val(mc)
		return len(stale_list)

	def process_prompt_request(self):
		log.info("Sleeping... process_time=%f attempt_count=%d host_count=%d attempts_run_in_loop=%d",
			self.loop_time, len(self.attempt_list), self.host_count.val(), self.attempts_run_in_loop)
		c_read, _, _ = select.select([self.sock], [], [], self.poll_time)
		for _sock in c_read:
			log.debug("Connection received. Sending data.")
			if _sock == self.sock:
				self.send_data(_sock)

	def send_data(self, conn):
		connection, client_address = conn.accept()
		try:
			_c_read, _, _ = select.select([connection], [], [], 2)

			recvdata = _c_read[0].recv(1024).decode('ascii').strip()
			if len(_c_read) == 0 or len(recvdata) == 0:
				instance_list = self.metric_data.keys()
			else:
				instance_list = recvdata.split(" ")
				log.info("List of instances requested: %s" % str(instance_list))
		except Exception as e:
			log.exception(e)


		try:
			_, _c_write, _ = select.select([], [connection], [], 2)
			if len(_c_write) < 1:
				connection.close()
				return

			for instance_name in instance_list:
				if instance_name not in self.metric_data:
					instance_tags = self.running_config.get("tags").copy()
					instance_tags.update(self.running_config.get(("instances", instance_name, "tags"), default={}))
					instance_down = InstanceMetric("up", 0, tags=instance_tags)
					_c_write[0].sendall(str(instance_down).encode('ascii'))
					continue
				metric_keys_list = list(self.metric_data[instance_name].keys())
				for metric_key in metric_keys_list:
					_c_write[0].sendall(str(self.metric_data[instance_name].get(metric_key, '')).encode('ascii', errors="ignore"))
			_c_write[0].close()
		except Exception as e:
			log.exception("Error sending data. %s" % str(e))
		connection.close()

	def signal_handler(self, signum, frame):
		if signum == signal.SIGHUP:
			self.reload_config = True
			self.keep_running = True
			log.info("HUP signal received. Reloading config")
			return
		if signum == signal.SIGINT:
			self.keep_running = False
			log.info("INT signal received. Stopping process")
			return

