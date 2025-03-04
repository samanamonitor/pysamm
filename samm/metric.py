import time
from datetime import datetime

class Tag:
	def __init__(self, key, value):
		self.key=key.replace(".", "_")
		self.value=value
	def __str__(self):
		return "%s=\"%s\"" % (self.key, self.value)


class InstanceMetric:
	def __init__(self, name, value, tags=None, prefix=None, stale_timeout=-1, value_mapping=None, none_is_zero=True):
		self.none_is_zero = none_is_zero
		name = name.replace(".", "_")
		if isinstance(prefix, str):
			self._name = "%s_%s" % (prefix, name)
		else:
			self._name=name

		if value_mapping and not isinstance(value_mapping, dict):
			raise TypeError("Invalid value_mapping. Expecting dict.")
		if value_mapping is None:
			self.value_mapping = { "*": -1 }
		else:
			self.value_mapping = value_mapping

		if isinstance(value, bool):
			self.value = int(value)
		elif isinstance(value, str) and value.replace('.', '').isnumeric():
			self.value = float(value)
		elif isinstance(value, (int, float)):
			self.value = value
		elif isinstance(self.value_mapping, dict) and isinstance(value, str):
			self.value = value
		elif value is None and self.none_is_zero:
			self.value = 0
		elif isinstance(value, datetime):
			self.value = value.timestamp() * 1000
		else:
			raise TypeError("Invalid value")

		if isinstance(tags, list):
			self._tags=tags.copy()
		elif isinstance(tags, dict):
			self._tags = []
			for key in tags:
				self._tags += [Tag(key, tags[key])]
		elif tags is None:
			self._tags = []
		else:
			raise TypeError("Invalid type for tags")

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
			self.key, self.val())

	def __repr__(self):
		return "<%s name=%s value=%s>" % (
			self.__class__.__name__, self._name, self.val())

	def val(self, *value):
		if len(value) > 0:
			self.value = value[0]
			self._last_update = time.time()

		value = self.value
		if isinstance(value, str) and self.value_mapping:
			default_mapping = self.value_mapping.get("*", -1)
			value = self.value_mapping.get(value, default_mapping)

		if not isinstance(value, (int, float)):
			value = -1

		return value

	def is_stale(self):
		if self._stale_timeout is None or self._stale_timeout < 0:
			return False
		if time.time() - self._last_update > self._stale_timeout:
			return True
		return False
