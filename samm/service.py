from .config import Config
from .attempt import Attempt
from .metric import InstanceMetric
from time import sleep, process_time, time
import socket, select, os, signal, sys
from random import Random
import threading
import logging

log = logging.getLogger(__name__)

class Service:

    def __init__(self, config_file):
        self.running_config = None
        self.keep_running = False
        self.rand = Random()
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
        self.keep_running = self.running_config._valid_config

        self.init_local_metrics()
        self.init_attempts()
        self.init_sock()
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def init_local_metrics(self):
        self.startup_time = InstanceMetric("startup_time", time(), self.tags)
        self.metric_count = InstanceMetric("metric_count", 0, self.tags)
        self.host_count   = InstanceMetric("host_count", 0, self.tags)
        self.scheduled_attempts = InstanceMetric("scheduled_attempts_count", 0, self.tags)
        self.running_time = InstanceMetric("running_time_seconds_count", 0, self.tags)
        self.metric_data_bytes = InstanceMetric("metric_data_bytes", 0, self.tags)
        self.thread_count = InstanceMetric("thread_count", 0, self.tags)
        self.pt = InstanceMetric("process_time_seconds_count", 0, self.tags)
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
        self.debug = self.running_config.get("debug", 0)
        logging.basicConfig(stream=sys.stdout, level=self.debug)
        self._stale_timeout = self.running_config.get("stale_timeout", default=600)
        self.poll_time = self.running_config.get("poll_time", default=5)
        self.tags = self.running_config.get('service_tags', default={}).copy()
        self.tags.update(self.running_config.get('tags'))

    def init_attempts(self):
        self.attempt_list = []
        self.host_count.val(0)
        self.scheduled_attempts.val(0)
        for instance_name in self.running_config.get("instances"):
            instance = self.running_config.get(("instances", instance_name))
            if instance.register:
                self.host_count.val(self.host_count.val() + 1)
                for check_name in instance.checks:
                    try:
                        a = Attempt(self.running_config, instance_name, check_name)
                        a.schedule(self.scheduled_attempts.val() * self.initial_spread
                            + int(self.rand.gauss(5, 5)))
                        self.attempt_list += [ a ]
                        self.scheduled_attempts.val(self.scheduled_attempts.val() + 1)
                    except Exception as e:
                        log.exception("Unable to create attempt for %s-%s. %s", instance_name, check_name, str(e))

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
        for attempt in self.attempt_list:
            try:
                if attempt.process(self.metric_data):
                    log.debug("Running attempt alias=%s instance_name=%s check_name=%s.",
                        attempt.alias, attempt.instance_name, attempt.check_name)
            except Exception as e:
                log.exception("Got error from Attempt.run() : %s - instance=%s check=%s",
                    str(e), attempt.instance_name, attempt.check_name)

    def process_loop(self):
        while self.keep_running:
            self.process_attempts()
            self.maintain_metric_data()
            self.process_prompt_request()
            if self.reload_config:
                self.load_config()
                self.reload_config = False
                self.init_attempts()
        self.keep_running = True

    def maintain_metric_data(self):
        self.metric_data_bytes.val(sys.getsizeof(self.metric_data_bytes))
        self.running_time.val(time() - self.startup_time.val())
        self.pt.val(process_time())
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
        log.debug("Sleeping... process_time=%f attempt_count=%d host_count=%d",
            process_time(), len(self.attempt_list), self.host_count.val())
        c_read, _, _ = select.select([self.sock], [], [], self.poll_time)
        for _sock in c_read:
            log.debug("Connection received. Sending data.")
            if _sock == self.sock:
                self.send_data(_sock)

    def send_data(self, conn):
        connection, client_address = conn.accept()
        _c_read, _, _ = select.select([connection], [], [], 2)

        if len(_c_read) == 0 or len(_c_read[0].recv(1024).decode('ascii').strip()) == 0:
            instance_list = self.metric_data.keys()
        else:
            instance_list = _c_read[0].recv(1024).decode('ascii').strip().split(" ")

        _, _c_write, _ = select.select([], [connection], [], 2)
        if len(_c_write) < 1:
            connection.close()
            return

        try:
            for instance_name in instance_list:
                if instance_name not in self.metric_data:
                    instance_tags = self.running_config.get("tags").copy()
                    instance_tags.update(self.running_config.get(("instances", instance_name, "tags")))
                    instance_down = InstanceMetric("up", 0, tags=instance_tags)
                    _c_write[0].sendall(str(instance_down).encode('ascii'))
                    continue
                for metric_key in self.metric_data[instance_name]:
                    _c_write[0].sendall(str(self.metric_data[instance_name][metric_key]).encode('ascii'))
            _c_write[0].close()
        except Exception as e:
            log.exception("Error sending data. %s" % str(e))
            connection.close()

    def signal_handler(self, signum, frame):
        if signum == signal.SIGHUP:
            self.reload_config = True
            self.keep_running = True
            log.info("HUP signal received. Reloading config", ERROR)
            return
        if signum == signal.SIGINT:
            self.keep_running = False
            log.info("INT signal received. Stopping process", ERROR)
            return

