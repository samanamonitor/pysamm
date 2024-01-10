from json import JSONEncoder
import uuid


class SammException(Exception):
    pass

class SammObjectEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, SammObject):
            return obj.__dict__
        return JSONEncoder.default(self, obj)

class SammObject:
    def __init__(self, object_definition, configuration=None):
        if not isinstance(object_definition, dict):
            raise TypeError("config must be dictionary.")
        if "object_type" not in object_definition:
            raise TypeError("config must have object_type set.")

        self._config = configuration
        self._attributes = {}

        self.use = object_definition.get("use", [])
        if isinstance(self.use, str):
            self.use = [ self.use ]
        self.register = object_definition.get("register", True)
        self.name = object_definition.get("name", str(uuid.uuid4()))

        for k in object_definition.keys():
            if k in [ "use", "register", "name" ]:
                continue
            self._attributes[k] = object_definition[k]
        self._config_section = "undefined"
        self._applied_templates = False

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
        return self._attributes.get(key, default)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, str(self._attributes))

    def apply_template(self, template_name):
        raise SammException("Unable to apply template to base class")

    def _post_process_internal(self):
        pass

    def post_process(self):
        if self._applied_templates:
            return
        for template_name in self.use:
            self._apply_template(template_name)
        self._post_process_internal()
        self._applied_templates = True

    def _apply_template(self, template_name):
        template = self._config.get((self._config_section, template_name))
        if template is None:
            raise SammException("Template %s defined in %s %s doesn't exist" % 
                (template_name, self.__class__.__name__.lower(), self.name))
        if not template._applied_templates:
            template.post_process()
        if template.__class__.__name__ != self.__class__.__name__:
            raise SammException("Invalid object type from template=%s" % template_name)
        for key, value in template._attributes.items():
            if isinstance(value, list):
                attribute = self._attributes.setdefault(key, [])
                attribute += value
            elif isinstance(value, dict):
                attribute = self._attributes.setdefault(key, {})
                attribute.update(value)
            else:
                self._attributes.setdefault(key, value)

    @property
    def __dict__(self):
        out = self._attributes.copy()
        out['name'] = self.name
        out['register'] = self.register
        out['use'] = self.use
        return out
