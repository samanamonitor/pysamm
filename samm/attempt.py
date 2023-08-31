from threading import Thread
from .metric import InstanceMetric

class Tag:
    def __init__(self, key, value):
        self.key=key
        self.value=value
    def __str__(self):
        return "%s=\"%s\"" % (self.key, self.value)


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
        self.tag_property = config.get(("checks", check_name, "tag_property"), resolve_vars=True, default=[])
        self.command="commands", config.get(("checks", check_name, "command"), resolve_vars=True)
        self.command_args=config.get(self.command + ("args",), 
            instance_name=instance_name, check_name=check_name, resolve_vars=True)
        self.module_name=config.get(self.command + ("type",), 
            instance_name=instance_name, check_name=check_name, resolve_vars=True)
        self.metrics = config.get(("checks", check_name, "metrics"))
        self.data = config.run_module(self.module_name, **self.command_args)
        self.thread = None
        self.instance_stale_timeout = config.get(("instances", instance_name, "stale_timeout"))
        self.check_stale_timeout = config.get(("checks", check_name, "stale_timeout"))
        self.base_tags = []
        self.add_base_tags(config.get(("tags"), {}))
        self.add_base_tags(config.get(("instances", instance_name, "tags"), default={}))
        self.add_base_tags(config.get(("checks", check_name, "tags"), default={}))
        self.add_base_tags({ "instance": self.instance_name })

    def add_base_tags(self, tags):
        for key in tags:
            self.base_tags += [ Tag(key, tags[key]) ]

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
        instance_name=self.instance_name.lower()
        instance_metric = metric_data.setdefault(instance_name, {})

        im_up = InstanceMetric("up", 1, self.base_tags, stale_timeout=self.instance_stale_timeout)
        try:
            instance_metric[im_up.key] = im_up
            for d in self.data:
                for m in self.metrics:
                    if m not in d:
                        continue
                    im = InstanceMetric(m.lower(), d[m], self.base_tags, prefix=self.alias.lower(), stale_timeout=self.check_stale_timeout)
                    for t in self.tag_property:
                        im.add_tag(Tag(t.lower(), str(d[t]).lower()))
                    instance_metric[im.key] = im
        except Exception as e:
            im_up.value = 0
            metric_data[instance_name] = { im_up.key:  im_up }
            raise

        if schedule_next:
            self.schedule_next()
        else:
            self.next_run = 0
        return True

    def schedule_next(self):
        self.schedule(self.check.get("check_interval"))

    def schedule(self, seconds):
        self.next_run = time.time() + seconds
