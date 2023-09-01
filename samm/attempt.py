from threading import Thread
from .metric import InstanceMetric
import time

class Attempt:
    def __init__(self, config, instance_name, check_name):
        self.check=config.get(("checks", check_name))
        if self.check is None:
            raise TypeError("Check %s not found" % check_name)
        self.instance=config.get(("instances", instance_name))
        self.next_run = 0
        self.instance_name=instance_name
        self.check_name = check_name
        self.alias = self.check.get('alias', check_name)
        self.command="commands", config.get(("checks", check_name, "command"), \
            resolve_vars=True)
        self.command_args=config.get(self.command + ("args",), 
            instance_name=instance_name, check_name=check_name, resolve_vars=True)
        self.module_name=config.get(self.command + ("type",), 
            instance_name=instance_name, check_name=check_name, resolve_vars=True)
        self.metrics = config.get(("checks", check_name, "metrics"))
        self.data = config.run_module(self.module_name, **self.command_args)
        self.thread = None
        self.instance_stale_timeout = config.get(("instances", instance_name, "stale_timeout"))
        self.check_stale_timeout = config.get(("checks", check_name, "stale_timeout"))
        self.tag_properties = config.get(("checks", check_name, "tag_properties"), \
                    resolve_vars=True, default=[])
        self.base_tags = {}
        self.base_tags.update(config.get(("tags"), default={}))
        self.base_tags.update(config.get(("instances", instance_name, "tags"), default={}))
        self.base_tags.update(config.get(("checks", check_name, "tags"), default={}))
        self.base_tags['instance'] = self.instance_name

    def due(self):
        if self.next_run == 0:
            return False
        return time.time() > self.next_run

    def process(self, metric_data):
        if not self.due() or (self.thread is not None and self.thread.is_alive()):
            return False
        self.thread = Thread(target=self.run, args=[metric_data])
        self.thread.start()
        return True

    def run(self, metric_data, schedule_next=True):
        self.next_run = 0
        instance_name=self.instance_name.lower()
        instance_metric = metric_data.setdefault(instance_name, {})

        im_up = InstanceMetric("up", 0, self.base_tags, stale_timeout=self.instance_stale_timeout)
        instance_metric[im_up.key] = im_up
        try:
            metric_received = 0
            for metric_data in self.data:
                metric_received = 1
                metric_tags = self.base_tags.copy()
                for tag_property in self.tag_properties:
                    metric_tags.update({tag_property.lower(): str(metric_data.get(tag_property, "none").lower())})

                for metric_name in self.metrics:
                    im = InstanceMetric(metric_name.lower(), metric_data.get(metric_name, -1), metric_tags, \
                        prefix=self.alias.lower(), stale_timeout=self.check_stale_timeout)
                    instance_metric[im.key] = im
            im_up.val(metric_received)
        except Exception as e:
            pass

        if schedule_next:
            self.schedule_next()

        return True

    def schedule_next(self):
        self.schedule(self.check.get("check_interval"))

    def schedule(self, seconds):
        self.next_run = time.time() + seconds
