class Instance:
    def __init__(self, config):
        if not isinstance(config, dict):
            raise TypeError("config must be dictionary.")
        if "object_type" not in config:
            raise TypeError("config must have object_type set to instance")

        self.__attributes = {}
        for k in config.keys():
            self.__attributes[k] = config[k]
        _ = self.__attributes.setdefault("register", True)
        _ = self.__attributes.setdefault("alias", self.name)
        _ = self.__attributes.setdefault("display_name", self.name)
        _ = self.__attributes.setdefault("address", None)
        _ = self.__attributes.setdefault("max_check_attempts", 3)
        _ = self.__attributes.setdefault("check_interval", 5)
        _ = self.__attributes.setdefault("retry_interval", self.check_interval)
        _ = self.__attributes.setdefault("active_checks_enabled", True)
        _ = self.__attributes.setdefault("checks", [])
        _ = self.__attributes.setdefault("tags", [])

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __getattr__(self, key):
        if key not in self.__attributes:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, key))
        return self.__attributes[key]

    def __repr__(self):
        r = "<Instance 'name': '%s', 'register': %s, 'address': '%s'>" % (
            self.name, self.register, self.address)
        return r

    def get(self, key, default=None):
        try:
            return self.__attributes[key]
        except AttributeError:
            return default


