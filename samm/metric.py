import time

class Tag:
    def __init__(self, key, value):
        self.key=key
        self.value=value
    def __str__(self):
        return "%s=\"%s\"" % (self.key, self.value)

class InstanceMetric:
    def __init__(self, name, value, tags=[], prefix=None):
        if isinstance(prefix, str):
            self._name = "%s_%s" % (prefix, name)
        else:
            self._name=name
        self.value=value
        self._tags=tags.copy()
    def add_tag(self, tag):
        self._tags += [tag]
    @property
    def tags(self):
        return ",".join([ str(x) for x in self._tags ])
    @property
    def key(self):
        return "%s{%s}" % (self._name, self.tags)
    def __str__(self):
        return "%s %s" % (
            self.key, self.value)

class Attempt:
    def __init__(self, config, instance_name, check_name):
        self.check=config.get(("checks", check_name))
        self.instance=config.get(("instances", instance_name))
        self.next_run = 0
        self.instance_name=instance_name
        self.check_name = check_name
        self.alias = self.check.get('alias', check_name)
        if self.alias is None:
            self.alias = check_name
        self.tag_property = config.get(("checks", check_name, "tag_property"))
        if self.tag_property is None:
            self.tag_property = []
        self.command="commands", config.get(("checks", check_name, "command"))
        args=config.get(self.command + ("args",), 
            instance_name=instance_name, check_name=check_name, resolve_vars=True)
        module_name=config.get(self.command + ("type",), 
            instance_name=instance_name, check_name=check_name, resolve_vars=True)
        self.metrics = config.get(("checks", check_name, "metrics"))
        self.data = config.run_module(module_name, **args)

    def due(self):
        if self.next_run == 0:
            return False
        return time.time() > self.next_run


    def run(self, metric_data, schedule_next=True):
        instance_name=self.instance_name.lower()
        base_tags = [ Tag("instance", instance_name), Tag("job", "samm") ]
        if instance_name not in metric_data:
            metric_data[instance_name] = {}

        instance_metric = metric_data[instance_name]
        im_up = InstanceMetric("up", 1, base_tags)
        try:
            instance_metric[im_up.key] = im_up
            for d in self.data:
                for m in self.metrics:
                    im = InstanceMetric(m.lower(), d[m], base_tags, prefix=self.alias.lower())
                    for t in self.tag_property:
                        im.add_tag(Tag(t.lower(), d[t].lower()))
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
