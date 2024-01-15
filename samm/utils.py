import sys, requests, json
from time import time, process_time
import logging

log = logging.getLogger(__name__)



class LokiStream:
	def __init__(self, submodule_str, loki_url, tags={}, tag_property={}, time_property=None, **kwargs):
		mod_str, _sep, class_str = submodule_str.rpartition('.')
		__import__(mod_str)
		iterable_class = getattr(sys.modules[mod_str], class_str)
		self.tag_property = tag_property
		self.iterable = iterable_class(**kwargs)
		self.initialized = False
		self.values = []
		self.time_property = time_property
		self.tags = tags
		self.loki_url = loki_url
		self.metrics = {
			'ls_events': 0,
			'ls_pull_process_time': 0,
			'ls_push_process_time': 0,
		}

	def set_tags(self, item):
		self.initialized = True
		for key, prop in self.tag_property.items():
			self.tags[key] = item[prop]

	def pull(self):
		self.values = []
		s = process_time()
		for item in self.iterable:
			if not self.initialized:
				self.set_tags(item)
			event_time = int(item.get(self.time_property, time()) * 1000000000)
			self.values += [[ str(event_time), json.dumps(dict(item)) ]]
		self.metrics['ls_pull_process_time'] = process_time() - s
		self.metrics['ls_events'] = len(self.values)

	def push(self):
		if self.metrics['ls_events'] == 0:
			self.metrics['ls_push_process_time'] = 0
			return
		s = process_time()
		headers = {
			'Content-type': 'application/json'
		}
		payload = {
			'streams': [ ]
		}
		payload['streams'] += [ {
			'stream': self.tags,
			'values': self.values
		}]
		p = json.dumps(payload)
		log.debug(p)
		self.answer = requests.post(self.loki_url, data=p, headers=headers)
		log.debug(self.answer.text)
		self.metrics['ls_push_process_time'] = process_time() - s

	def __iter__(self):
		self.pull()
		self.push()
		self._sent = 0
		return self

	def __next__(self):
		if self._sent:
			raise StopIteration
		self._sent = 1
		return { **self.metrics, **self.tags }


class FilterFunction:
	def adsecondsfromnow(seconds):
		if not isinstance(seconds, int):
			seconds = int(seconds)
		return int(time() - seconds + 11644473600) * 10000000

	def lastlogon_to_timestamp(ll):
		if isinstance(ll, list) and len(ll) > 0:
			ll = ll[0]
		if isinstance(ll, bytes):
			ll = ll.decode('ascii')
		return (int(ll) / 10000000) - 11644473600

	def filter_dict_to_string(filter_dict):
		'''This function converts dictionary to ldap filter string.
		TODO: allow for more complex expressions. Now only accepts AND for all
			  elements in the expression
		'''
		if not isinstance(filter_dict, dict):
			raise TypeError("Invalid filter. Must be dictionary")
		operator_mapping = {
			"eq": "=",
			"le": "<=",
			"ge": ">=",
			"px": "~="
		}
		filterlist = []
		for attribute, value in filter_dict.items():
			if not isinstance(value, dict):
				raise TypeError("Invalid filter expression. Value must be a dictionary. %s" % filter_dict)
			filterstr = attribute
			try:
				op, value = next(iter(value.items()))
			except StopIteration:
				raise TypeError("Invalid filter expression. Value dictionary must have at least one element. %s" \
					% filter_dict)
			try:
				filterstr += operator_mapping[op]
			except KeyError:
				raise TypeError("Invalid filter expression. Only values allowed for operator are: eq, ge, le, px. %s" \
					 % filter_dict)
			if isinstance(value, dict):
				func_name, param = next(iter(value.items()))
				if func_name[:4] != "Fn::":
					raise TypeError("Expecting function. Use syntax Fn::<function name>. %s" % filter_dict)
				func_name = func_name[4:]
				func = getattr(FilterFunction, func_name)
				value = func(*param)
			filterstr += str(value)
			filterlist += [ "(%s)" % filterstr ]
		if len(filterlist) < 1:
			raise TypeError("Invalid filter. Dictonary cannot be empty. %s" % filter_dict)
		if len(filterlist) > 1:
			return "(&%s)" % "".join(filterlist)
		return filterlist[0]
