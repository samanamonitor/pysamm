import time

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
