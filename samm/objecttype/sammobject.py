from json import JSONEncoder
import uuid


class SammException(Exception):
	pass

class SammObject:
	def __init__(self, object_definition, configuration=None):
		if not isinstance(object_definition, dict):
			raise TypeError("config must be dictionary.")
		if "object_type" not in object_definition:
			raise TypeError("config must have object_type set.")

		self._config = configuration
		self._object_definition = object_definition
		self.pre_process()

	def pre_process(self):
		self._attributes = {}
		self.use = self._object_definition.get("use", [])
		if isinstance(self.use, str):
			self.use = [ self.use ]
		self.register = self._object_definition.get("register", True)
		self.name = self._object_definition.get("name", str(uuid.uuid4()))
		self.tags = self._object_definition.get("tags", {})

		for k in self._object_definition.keys():
			if k in [ "use", "register", "name", "tags" ]:
				continue
			self._attributes[k] = self._object_definition[k]
		self._config_section = "undefined"
		self._applied_templates = False

	def reprocess(self):
		self.pre_process()
		self.post_process()

	@property
	def config_section(self):
		return self._config_section

	def resolve(self, **kwargs):
		return False

	def __getitem__(self, key):
		return self.__getattribute__(key)

	def __getattr__(self, key):
		if key not in self._attributes:
			raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, key))
		return self._attributes[key]

	def get(self, key, default=None):
		if key == 'tags':
			return self.tags
		if key == 'name':
			return self.name
		if key == 'register':
			return self.register
		return self._attributes.get(key, default)

	def __repr__(self):
		return "<%s name=%s register=%s tags=%s %s>" % (
			self.__class__.__name__, 
			self.name,
			self.register,
			self.tags,
			str(self._attributes)
			)

	def apply_template(self, template_name):
		raise SammException("Unable to apply template to base class")

	def post_process(self):
		if self._applied_templates:
			return
		for template_name in self.use:
			self._apply_template(template_name)

	def _apply_template(self, template_name):
		template = self._config.get((self._config_section, template_name))
		if template is None:
			raise SammException("Template %s defined in %s %s doesn't exist" % 
				(template_name, self.__class__.__name__.lower(), self.name))
		if template.__class__.__name__ != self.__class__.__name__:
			raise SammException("Invalid object type from template=%s" % template_name)
		template.post_process()
		self.tags.update(template.tags)
		for key, value in template._attributes.items():
			if isinstance(value, list):
				attribute = self._attributes.setdefault(key, [])
				attribute += value
			elif isinstance(value, dict):
				attribute = self._attributes.setdefault(key, {})
				if isinstance(attribute, dict):
					attribute.update(value)
			else:
				self._attributes.setdefault(key, value)

	def merge_object_definition(self, object_definition):
		self.tags.update(object_definition.get('tags', {}))
		use = object_definition.get('use', [])
		for u in use:
			if u not in self.use:
				self.use.append(u)

	@property
	def __dict__(self):
		out = self._attributes.copy()
		out['name'] = self.name
		out['register'] = self.register
		out['tags'] = self.tags
		return out
