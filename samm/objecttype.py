class SammObject:
    def __init__(self, object_definition, configuration=None):
        if not isinstance(object_definition, dict):
            raise TypeError("config must be dictionary.")
        if "object_type" not in object_definition:
            raise TypeError("config must have object_type set to instance")

        self._config = configuration
        self._attributes = {}
        for k in object_definition.keys():
            self._attributes[k] = object_definition[k]

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __getattr__(self, key):
        if key not in self._attributes:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, key))
        return self._attributes[key]

    def get(self, key, default=None):
        try:
            return self._attributes[key]
        except AttributeError:
            return default

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, str(self._attributes))


class Instance(SammObject):
    def __init__(self, object_definition, configuration=None):
        super(Instance, self).__init__(object_definition, configuration)
        _ = self._attributes.setdefault("register", True)
        _ = self._attributes.setdefault("alias", self.name)
        _ = self._attributes.setdefault("display_name", self.name)
        _ = self._attributes.setdefault("address", None)
        _ = self._attributes.setdefault("max_check_attempts", 3)
        _ = self._attributes.setdefault("check_interval", 5)
        _ = self._attributes.setdefault("retry_interval", self.check_interval)
        _ = self._attributes.setdefault("active_checks_enabled", True)
        _ = self._attributes.setdefault("checks", [])
        _ = self._attributes.setdefault("tags", [])


class Command(SammObject):
    def __init__(self, object_definition, configuration=None):
        super(Command, self).__init__(object_definition, configuration)
        _ = self._attributes.setdefault("register", True)


class Check(SammObject):
    def __init__(self, config, configuration=None):
        super(Check, self).__init__(config, configuration)
        _ = self._attributes.setdefault("register", True)

