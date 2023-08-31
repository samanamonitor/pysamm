from .config import Config
from .metric import Attempt, InstanceMetric, Tag
from time import sleep, process_time, time
import socket, select, os, signal, sys
from random import Random
import threading

ERROR=0
WARNING=1
INFO=2

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
        self.config_path, sep, self.config_file = config_file.rpartition("/")
        self.load_config()
        if self.running_config._valid_config:
            self.keep_running = True
        os.chdir(self.running_config.get("base_dir"))

        self._stale_timeout = self.running_config.get("stale_timeout", 600)
        self.polltime = self.running_config.get("polltime", 5)
        self.attempt_list = []
        self.base_tags = [ 
            Tag("instance", self.running_config.setdefault("base_tags", {}).setdefault("instance", "samm")), 
            Tag("job", self.running_config.setdefault("base_tags", {}).setdefault("job", "samm"))
            ]
        self.startup_time = InstanceMetric("startup_time", time(), self.base_tags)
        self.metric_count = InstanceMetric("metric_count", 0, self.base_tags)
        self.host_count   = InstanceMetric("host_count", 0, self.base_tags)
        self.scheduled_attempts = InstanceMetric("scheduled_attempts_count", 0, self.base_tags)
        self.running_time = InstanceMetric("running_time_seconds_count", 0, self.base_tags)
        self.metric_data_bytes = InstanceMetric("metric_data_bytes", 0, self.base_tags)
        self.thread_count = InstanceMetric("thread_count", 0, self.base_tags)
        self.pt = InstanceMetric("process_time_seconds_count", 0, self.base_tags)
        self.metric_data = { 
            "samm": {
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

        self.init_attempts()
        self.init_sock()
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def load_config(self):
        self.running_config=Config(self.abs_config_file)
        self.running_config.reload()
        self.debug = self.running_config.get("debug", default=ERROR)

    def init_attempts(self):
        self.attempt_list = []
        self.host_count.val(0)
        self.scheduled_attempts.val(0)
        for instance_name in self.running_config.get("instances"):
            instance = self.running_config.get("instances")[instance_name]
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
                        self.log("Unable to create attempt for %s-%s. %s" % (instance_name, check_name, str(e)))

    def init_sock(self):
        self.sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock_file=self.running_config.get("sock_file")
        if os.path.exists(sock_file):
            os.unlink(sock_file)
        self.sock.bind(sock_file)
        os.chmod(sock_file, 0x0777)
        self.sock.listen(1)

    def process_attempts(self):
        for attempt in self.attempt_list:
            try:
                if attempt.process(self.metric_data):
                    self.log("Running attempt alias=%s instance_name=%s check_name=%s." 
                        % (attempt.alias, attempt.instance_name, attempt.check_name), INFO)
            except Exception as e:
                self.log("Got error from Attempt.run() : %s - instance=%s check=%s" 
                    % (str(e), attempt.instance_name, attempt.check_name), ERROR)

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
            self.log("Cleanup metric %s.%s" % s)

        self.metric_count.val(mc)
        return len(stale_list)

    def process_prompt_request(self):
        self.log("Sleeping... process_time=%f attempt_count=%d host_count=%d" % 
            (process_time(), len(self.attempt_list), self.host_count.val()), INFO)
        c_read, _, _ = select.select([self.sock], [], [], self.polltime)
        for _sock in c_read:
            self.log("Connection received. Sending data.")
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
                    _c_write[0].sendall(("up{job=\"samm\",instance=\"%s\"} 0\n" % 
                        (instance_name)).encode('ascii'))
                for metric_key in self.metric_data[instance_name]:
                    _c_write[0].sendall(str(self.metric_data[instance_name][metric_key]).encode('ascii'))
            _c_write[0].close()
        except Exception as e:
            self.log("Error sending data")
            connection.close()

    def signal_handler(self, signum, frame):
        if signum == signal.SIGHUP:
            self.reload_config = True
            self.keep_running = True
            self.log("HUP signal received. Reloading config", ERROR)
            return
        if signum == signal.SIGINT:
            self.keep_running = False
            self.log("INT signal received. Stopping process", ERROR)
            return

    def log(self, msg, level=INFO):
        if self.debug >= level:
            print("%d - (%d) - %s" % (time(), self.debug, msg))
