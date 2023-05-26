import time

class Attempt:
    def __init__(self, config, instance_name, check_name):
        self.check=config.get("checks." + check_name)
        self.instance=config.get("instances." + instance_name)
        self.next_run = 0
        self.instance_name=instance_name
        self.check_name = check_name
        self.alias = self.check['alias']
        if self.alias is None:
            self.alias = check_name
        self.tag_property = config.get("checks." + check_name + ".tag_property")
        if self.tag_property is None:
            self.tag_property = []
        self.command="commands." + config.get("checks." + check_name + ".command")
        args=config.get(self.command + ".args", instance_name=instance_name, check_name=check_name, resolve_vars=True)
        module_name=config.get(self.command + ".type", instance_name=instance_name, check_name=check_name, resolve_vars=True)
        self.metrics = config.get("checks." + check_name + ".metrics")
        self.data = config.run_module(module_name, **args)

    def run(self, metric_data):
        if time.time() < self.next_run:
            return False
        for d in self.data:
            for m in self.metrics:
                tags=[ "instance=\"%s\"" % self.instance_name.lower() ]
                for t in self.tag_property:
                    tags += [ "%s=\"%s\"" % (t, d[t])]
                metric_data["%s_%s{%s}" % (self.alias.lower(), m.lower(), ",".join(tags).lower())] = d[m]
        self.next_run = 0
        return True

    def schedule_next(self):
        self.schedule(self.check.get("check_interval"))

    def schedule(self, seconds):
        self.next_run = time.time() + seconds
