import time

class Tag:
    def __init__(self, key, value):
        self.key=key
        self.value=value
    def __str__(self):
        return "%s=\"%s\"" % (self.key, self.value)

class InstanceMetric:
    def __init__(self, name, value, tags=[], prefix=None, stale_timeout=-1):
        if isinstance(prefix, str):
            self._name = "%s_%s" % (prefix, name)
        else:
            self._name=name
        self.value=value
        self._tags=tags.copy()
        self._last_update = time.time()
        self._stale_timeout = stale_timeout

    def add_tag(self, tag):
        self._tags += [tag]
    @property
    def tags(self):
        return ",".join([ str(x) for x in self._tags ])
    @property
    def key(self):
        return "%s{%s}" % (self._name, self.tags)
    def __str__(self):
        return "%s %s\n" % (
            self.key, self.value)
    def val(self, *value):
        if len(value) == 0:
            return self.value
        else:
            self.value = value[0]
            self._last_update = time.time()
    def is_stale(self):
        if self._stale_timeout is None or self._stale_timeout < 0:
            return False
        if time.time() - self._last_update > self._stale_timeout:
            return True
        return False

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
        self.tag_property += config.get(("instances", instance_name, "tag_property"), resolve_vars=True, default=[])
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

    def due(self):
        if self.next_run == 0:
            return False
        return time.time() > self.next_run

    def process(self, metric_data):
        if not self.due() or (self.thread is not None and self.thread.is_alive()):
            return
        self.thread = Thread(target=self.run, args=[metric_data])
        self.thread.run()

    def run(self, metric_data, schedule_next=True):
        instance_name=self.instance_name.lower()
        base_tags = [ Tag("instance", instance_name), Tag("job", "samm") ]
        if instance_name not in metric_data:
            metric_data[instance_name] = {}

        instance_metric = metric_data[instance_name]
        im_up = InstanceMetric("up", 1, base_tags, stale_timeout=self.instance_stale_timeout)
        try:
            instance_metric[im_up.key] = im_up
            for d in self.data:
                for m in self.metrics:
                    im = InstanceMetric(m.lower(), d[m], base_tags, prefix=self.alias.lower(), stale_timeout=self.check_stale_timeout)
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
