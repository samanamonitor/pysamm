from .config import Config
from .metric import Attempt, InstanceMetric, Tag
from time import sleep, process_time, time
import socket, select, os, signal, sys
from random import Random
from threading import Thread

ERROR=0
WARNING=1
INFO=2

class Service:
    polltime = 5
    attempt_list = []
    base_tags = [ Tag("instance", "samm"), Tag("job", "samm") ]
    startup_time = InstanceMetric("startup_time", time(), base_tags)
    metric_count = InstanceMetric("metric_count", 0, base_tags)
    host_count   = InstanceMetric("host_count", 0, base_tags)
    scheduled_attempts = InstanceMetric("scheduled_attempts_count", 0, base_tags)
    running_time = InstanceMetric("running_time_seconds_count", 0, base_tags)
    metric_data_bytes = InstanceMetric("metric_data_bytes", 0, base_tags)
    pt = InstanceMetric("process_time_seconds_count", 0, base_tags)
    metric_data = { 
        "samm": {
            startup_time.key: startup_time,
            metric_count.key: metric_count,
            host_count.key: host_count,
            scheduled_attempts.key: scheduled_attempts,
            running_time.key: running_time,
            pt.key: pt
            metric_data_bytes.key: metric_data_bytes
        }
    }
    running_config = None
    rand = Random()
    sock = None
    debug = 0
    config_path = ""
    config_file = ""
    keep_running = True
    reload_config = False
    stop_loop = True
    initial_spread = 1

    def __init__(self, config_file):
        self.abs_config_file = os.path.abspath(config_file)
        self.config_path, sep, self.config_file = config_file.rpartition("/")
        self.load_config()
        os.chdir(self.running_config.get("base_dir"))
        self.init_attempts()
        self.init_sock()
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def load_config(self):
        self.running_config=Config(self.abs_config_file)
        self.debug = self.running_config.get("debug", default=ERROR)

    def init_attempts(self):
        self.attempt_list = []
        self.host_count.value = 0
        self.scheduled_attempts.value = 0
        for instance_name in self.running_config.get("instances"):
            instance = self.running_config.get("instances")[instance_name]
            if instance.register:
                self.host_count.value += 1
                for check_name in instance.checks:
                    a = Attempt(self.running_config, instance_name, check_name)
                    a.schedule(self.scheduled_attempts.value * self.initial_spread
                        + int(self.rand.gauss(5, 5)))
                    self.attempt_list += [ a ]
                    self.scheduled_attempts.value += 1

    def init_sock(self):
        self.sock=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock_file=self.running_config.get("sock_file")
        if os.path.exists(sock_file):
            os.unlink(sock_file)
        self.sock.bind(sock_file)
        os.chmod(sock_file, 0x0777)
        self.sock.listen(1)

    def process_loop(self):
        while self.keep_running:
            for a in self.attempt_list:
                if not a.due(): continue
                try:
                    t = Thread(target=a.run, args=[self.metric_data])
                    t.run()
                    self.log("Running attempt alias=%s instance_name=%s check_name=%s." 
                        % (a.alias, a.instance_name, a.check_name), INFO)
                except Exception as e:
                    self.log("Got error from Attempt.run() : %s" % str(e), ERROR)
            self.log("Sleeping... process_time=%f attempt_count=%d host_count=%d" % 
                (process_time(), len(self.attempt_list), self.host_count.value), INFO)
            c_read, c_write, in_error = select.select([self.sock], [], [], self.polltime)
            self.metric_data_bytes.value = sys.getsizeof(self.metric_data_bytes)
            self.running_time.value = time() - self.startup_time.value
            self.pt.value = process_time()
            for c in c_read:
                if c == self.sock:
                    self.send_data(c)
            if self.reload_config:
                self.load_config()
                self.reload_config = False
                self.init_attempts()
        self.keep_running = True

    def send_data(self, conn):
        connection, client_address = conn.accept()
        for instance_name in self.metric_data:
            for metric_key in self.metric_data[instance_name]:
                connection.sendall(("%s\n" % 
                    (self.metric_data[instance_name][metric_key])).encode('ascii'))
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
