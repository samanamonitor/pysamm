from .sammobject import SammObject
from samm.utils import FilterFunction
import samm
import logging
import ldap
import uuid
import json
from time import time

log = logging.getLogger(__name__)

class Discovery(SammObject):
	def __init__(self, object_definition, configuration=None):
		super(Discovery, self).__init__(object_definition, configuration)

	def pre_process(self):
		super(Discovery, self).pre_process()
		self._config_section = "discoveries"
		self._next_run = 0

	def post_process(self):
		super(Discovery, self).post_process()
		attributes = {}
		for attribute_name, value in self._attributes.items():
			attributes[attribute_name] = self._config.replace_vars(value, discovery_name=self.name)
		if self.discovery_type == "active_directory" and self.register == True:
			self.method = ActiveDirectoryDiscovery(name=self.name, tags=self.tags,
				configuration=self._config, **attributes)
		else:
			self.method = None
		self._applied_templates = True

	def schedule(self, seconds=None):
		if seconds == None:
			seconds = self.ldap_refresh_seconds
		self._next_run = time() + seconds
		return self._next_run

	def run(self, force=False):
		discovered_objects = []
		if not self.register:
			return discovered_objects
		if not force and time() < self._next_run:
			return discovered_objects
		self.reprocess()
		discovered_objects = list(self.method)
		log.info("Refreshing discovered objects. %s Objects discovered=%d" % (
			self.name,
			len(discovered_objects)))
		self.schedule()
		return discovered_objects

	@property
	def __dict__(self):
		out = super(Discovery, self).__dict__
		if self.method is not None:
			out['method_type'] = self.method.__class__.__name__
			out['method'] = self.method.__dict__
		else:
			out['method_type'] = None
			out['method'] = None
		return out

class ActiveDirectoryDiscovery:
	def __init__(self, /, use=None, configuration=None, **kwargs):
		self.name = kwargs.get('name', uuid.uuid4())
		self.ldap_url = kwargs.get('ldap_url')
		self.ldap_dn = kwargs.get('ldap_dn')
		self.ldap_password = kwargs.get('ldap_password')
		self.ldap_base = kwargs.get('ldap_base')
		self.ldap_scope = ldap.__getattribute__(kwargs.get('ldap_scope'))
		self.tags = kwargs.get('tags', {})
		self._config = configuration

		ldap_filter = kwargs.get('ldap_filter')
		if isinstance(ldap_filter, dict):
			keys = list(ldap_filter.keys())
			if len(keys) == 1 and keys[0][:4] == "Fn::":
				self.ldap_filter = self._config.replace_vars(ldap_filter, discovery_name=self.name)
			else:
				self.ldap_filter = FilterFunction.filter_dict_to_string(ldap_filter)
		elif isinstance(ldap_filter, str):
			self.ldap_filter = ldap_filter
		elif isinstance(ldap_filter, list):
			self.ldap_filter = "".join(ldap_filter)
		else:
			raise TypeError("Attribute ldap_filter must be a dictionary (%s)" % self.name)
		ldap_attrlist = kwargs.get('ldap_attrlist')
		if not isinstance(ldap_attrlist, list):
			self.ldap_attrlist = [ ldap_attrlist ]
		else:
			self.ldap_attrlist = ldap_attrlist

		self.ldap_refresh_seconds = kwargs.get('ldap_refresh_seconds')
		self.ldap_attribute_tags = kwargs.get('ldap_attribute_tags')
		self.object_type = kwargs.get('discovery_object_type')
		self.ldap_attribute_object_map = kwargs.get('ldap_attribute_object_map')
		self.tags = kwargs.get('tags', {})
		self.object_use = kwargs.get('object_use', [])
		test_file = kwargs.get('test_file')
		self._test_data = None
		if test_file is not None:
			with open(test_file, "r") as f:
				data = f.read()
				self._test_data = eval(data)


	def __iter__(self):
		if isinstance(self._test_data, list):
			self._test_iter = iter(self._test_data)
			return self
		self._conn = ldap.initialize(self.ldap_url)
		self._conn.simple_bind_s(self.ldap_dn, self.ldap_password)
		self._conn.set_option(ldap.OPT_REFERRALS, 0)
		self._search_id = self._conn.search(self.ldap_base, self.ldap_scope, 
				self.ldap_filter, self.ldap_attrlist)
		return self

	def __next__(self):
		if isinstance(self._test_data, list):
			(result_type, items) = next(self._test_iter)
		else:
			(result_type, items) = self._conn.result(msgid=self._search_id, all=0)
		if result_type == ldap.RES_SEARCH_RESULT:
			raise StopIteration
		if result_type != ldap.RES_SEARCH_ENTRY:
			return self.__next__()
		return self._ldap_to_object_definition(items[0])

	def _ldap_to_object_definition(self, item):
		log.debug(str(item))
		object_definition = {
			"object_type": self.object_type,
			"tags": self.tags.copy()
		}
		log.debug(str(object_definition))
		ldap_instance_dict = item[1]
		if not isinstance(ldap_instance_dict, dict):
			raise StopIteration
		ldap_instance_dict.update({"dn": item[0]})
		for object_attr, ldap_attr in self.ldap_attribute_object_map.items():
			value = ldap_list_bytes_to_string(ldap_instance_dict[ldap_attr]).lower()
			object_definition[object_attr] = value
		for tag_name, ldap_attribute_name in self.ldap_attribute_tags.items():
			value = ldap_list_bytes_to_string(ldap_instance_dict[ldap_attribute_name]).lower()
			object_definition['tags'][tag_name] = value
		object_definition['use'] = self.object_use.copy()

		return object_definition

	@property
	def __dict__(self):
		return {
			"name": self.name,
			"ldap_url": self.ldap_url,
			"ldap_dn": self.ldap_dn,
			"ldap_password": self.ldap_password,
			"ldap_base": self.ldap_base,
			"ldap_scope": self.ldap_scope,
			"tags": self.tags,
			"ldap_filter": self.ldap_filter,
			"ldap_attrlist": self.ldap_attrlist,
			"ldap_refresh_seconds": self.ldap_refresh_seconds,
			"ldap_attribute_tags": self.ldap_attribute_tags,
			"object_type": self.object_type,
			"ldap_attribute_object_map": self.ldap_attribute_object_map,
			"object_use": self.object_use
		}

def ldap_list_bytes_to_string(data):
	if isinstance(data, list):
		data = data[0]
	if isinstance(data, bytes):
		data = data.decode('ascii')
	return data


