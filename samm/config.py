import re, os, json, sys
from .utils import FilterFunction
from . import objecttype
import logging

log = logging.getLogger(__name__)

class Config():
	def __init__(self, config_file):
		self._valid_config = False
		self.config_file = config_file
		self.modules = {}
		self._config = None
		log.debug("Config object created with file %s", config_file)

	def reload(self):
		object_definition_list = []
		self.load_base()
		object_definition_list = self.load_objects()
		self.process_objects(object_definition_list)
		object_definition_list = self.discover_objects()
		self.process_objects(object_definition_list)
		self._valid_config = True
		return self._valid_config

	def load_base(self):
		with open(self.config_file) as f:
			log.debug("Config file %s opened for loading.", self.config_file)
			try:
				self._config = json.load(f)
			except Exception as e:
				log.exception("Unable to load config file %s.", self.config_file)
				raise

		if "base_dir" not in self._config:
			raise KeyError("missing base_dir")
		if not os.path.exists(self._config['base_dir']):
			raise FileNotFoundError("Directory not found. base_dir=%s" % self._config['base_dir'])
		self._config['base_dir'] = os.path.abspath(self._config['base_dir'])

		if "config_dir" not in self._config:
			raise KeyError("missing config_dir")
		self._config['config_dir'] = os.path.join(self._config['base_dir'], self._config['config_dir'])
		if not os.path.exists(self._config['config_dir']):
			raise FileNotFoundError("Directory not found config_dir=%s" % self._config['config_dir'])

		if "resource_file" not in self._config:
			raise KeyError("missing resource_file")

		self.resource_file_path = os.path.join(self._config['config_dir'], self._config['resource_file'])
		with open(self.resource_file_path) as f:
			try:
				self._config["resources"] = json.load(f)
			except Exception as e:
				log.exception("Unable to load config file %s.", self._config["resources"])
				raise

		if not isinstance(self._config.get('object_files'), list):
			raise TypeError("Parameter object_files must be a list.")
		_ = self._config.setdefault("tags", {}).setdefault("job", "samm")

	def load_objects(self):
		object_definition_list = []
		for c in self._config['object_files']:
			object_file_path = os.path.join(self._config['config_dir'], c)
			log.debug("Loading config file %s", object_file_path)
			object_definition_list += self.load_object_file(object_file_path)
		return object_definition_list


	def load_object_file(self, filename):
		c=None
		object_definition_list = []
		with open(filename) as f:
			try:
				c=json.load(f)
			except Exception as e:
				log.exception("Unable to load config file %s.", filename)
				raise

		if not isinstance(c, list):
			raise TypeError("Invalid config type. Must be list")
		for o in c:
			if not isinstance(o, dict):
				raise TypeError("Invalid config type at file=%s. Expecting dict. data=%s" %
					(filename, str(o)))
			if "object_type" not in o:
				raise KeyError("Mandatory \'object_type\' missing at file=%s. data=%s" %
					(filename, str(o)))
			if "name" not in o:
				raise KeyError("Mandatory \'name\' missingat file=%s. data=%s" %
					(filename, str(o)))
			object_definition_list += [ o ]
		return object_definition_list

	def discover_objects(self):
		object_definition_list = []
		for discovery_name, discovery in self._config.get("discoveries", {}).items():
			discovery.reprocess()
			object_definition_list += discovery.run()
		return object_definition_list

	def process_objects(self, object_definition_list):
		objects = []
		for object_definition in object_definition_list:
			obj = self.load_single_object(object_definition)
			if obj is not None:
				objects.append(obj)

		for obj in objects:
			log.debug("Running post-process for %s:%s" %
				(obj.__class__.__name__.lower(), obj.name))
			obj.post_process()
		return objects

	def load_single_object(self, object_definition):
		obj = None
		try:
			object_class = objecttype.__getattribute__(object_definition["object_type"])
			obj = object_class(object_definition, self)
			config_section = self._config.setdefault(obj.config_section, {})
			if obj.name in config_section:
				obj = config_section[obj.name]
				obj.merge_object_definition(object_definition)
				log.debug("Merging definition %s name=%s register=%s" %
					(object_definition["object_type"], object_definition["name"], obj.register))
			else:
				config_section[obj.name] = obj
				log.debug("Creating new %s name=%s register=%s" %
					(object_definition["object_type"], object_definition["name"], obj.register))
		except AttributeError:
			log.exception("Invalid object_type %s" % object_definition["object_type"])
		return obj

	def setdefault(self, key, value):
		return self._config.setdefault(key, value)

	def get(self, in_data, instance_name=None, check_name=None, resolve_vars=False, default=None, default_variable=""):
		if isinstance(in_data, str):
			path = tuple(in_data.split("."))
		elif isinstance(in_data, list):
			path = tuple(in_data)
		elif isinstance(in_data, tuple):
			path = in_data
		else:
			raise TypeError(in_data)
		if path[0] == "instance":
			path = ( "instances", instance_name ) + path[1:]
		if path[0] == "check":
			path = ( "checks", check_name ) + path[1:]
		curconfig=self._config

		for p in path:
			curconfig = curconfig.get(p, None)
			if curconfig is None:
				break

		if resolve_vars == False:
			if curconfig is None and default is not None:
				return default
			return curconfig

		return self.replace_vars(curconfig, instance_name=instance_name,
			check_name=check_name, default=default, default_variable=default_variable)

	def run_module(self, module_str, **kwargs):
		if module_str not in self.modules:
			log.debug("Loading module %s", module_str)
			self.import_class(module_str)
		return self.modules[module_str](**kwargs)

	def import_class(self, import_str):
		if import_str in self.modules:
			return
		mod_str, _sep, class_str = import_str.rpartition('.')
		__import__(mod_str)
		try:
			self.modules[import_str] = getattr(sys.modules[mod_str], class_str)
		except AttributeError:
			log.exception('Class %s cannot be found', class_str)
			raise

	def get_variables(self, s):
		'''This function receives a string containing text and variables in the form $(variable_name)
		and will return a list of variable names. It can detect multiple variables.
		Variable names cannot contain the following characters (,),\\ or quotes'''
		var_regex=r'(?<!\\)\$\(([^\)]+)\)'
		varlist=re.findall(var_regex, s)
		return varlist

	def replace_vars(self, o, instance_name=None, check_name=None, default=None, default_variable=""):
		out=None
		if isinstance(o, str):
			'''
			We don't need to continue recursion. Just find variables and replace them
			'''
			variables=self.get_variables(o)
			out=o
			if not isinstance(default, str):
				defaut = ""
			for v in variables:
				if v[:4] == 'Fn::':
					func, args = v.split(' ', 1)
					args = tuple(args.split(' '))
					try:
						func = getattr(FilterFunction, func[4:])
						var_value = str(func(*args))
					except AttributeError:
						log.exception("Invalid function %s" % func)
						raise
					except Exception:
						log.exception("Error processing function %s" % func)
						raise
				else:
					var_value=self.get(v, instance_name=instance_name, check_name=check_name,
						resolve_vars=True, default=default)
				if isinstance(var_value, str):
					out=o.replace("$(%s)" % v, var_value)
				elif o == "$(%s)" % v:
					out=var_value
				else:
					raise TypeError("Unable to parse variable %s." % o)
		elif isinstance(o, list):
			'''
			We need to process recursively for each item in the list
			'''
			out = [None] * len(o)
			for i in range(len(o)):
				out[i] = self.replace_vars(o[i], instance_name=instance_name,
					check_name=check_name, default=default)
		elif isinstance(o, dict):
			'''
			We need to process recursively for each item in the dict
			'''
			out = {}
			for i in o:
				out[i] = self.replace_vars(o[i], instance_name=instance_name, check_name=check_name)
		elif isinstance(o, (int, float)):
			out = o
		else:
			out = default
		return out

	@property
	def __dict__(self):
		'''TODO: generalize the objects section'''
		return {
			"config_file": self.config_file,
			"config": {
				"base_dir": self._config['base_dir'],
				"config_dir": self._config['config_dir'],
				"resource_file": self._config['resource_file'],
				"resources": self._config['resources'],
				"object_files": self._config['object_files'],
				"objects": {
					"instances": [ i.__dict__ for name, i in self._config.get('instances', {}).items() ],
					"checks": [ i.__dict__ for name, i in self._config.get('checks', {}).items() ],
					"commands": [ i.__dict__ for name, i in self._config.get('commands', {}).items() ],
					"discoveries": [ i.__dict__ for name, i in self._config.get('discoveries', {}).items() ]
				}
			}
		}
