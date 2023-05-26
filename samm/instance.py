class Instance:
    name="Undefined"
    register=False
    alias="Undefined"
    address="Undefined"
    display_name="Undefined"
    parents=[]
    instancegroups=[]
    check_command=None
    up=1
    max_check_attempts=3
    check_interval=5
    retry_interval=3
    active_checks_enabled=True
    last_check=0

    def __init__(self, config):
        if not isinstance(config, dict):
            raise TypeError("config must be dictionary.")
        if "object_type" not in config:
            raise TypeError("config must have object_type set to instance")
        if "name" not in config:
            raise TypeError("name")
        self.name=config["name"]
        self.register = config.get("register", 1)
        self.alias = config.get("alias", self.name)
        self.address = config.get("address", None)
        self.display_name = config.get("display_name", self.name)
        self.max_check_attempts = config.get("max_check_attempts", 3)
        self.check_interval = config.get("check_interval", 5)
        self.retry_interval = config.get("retry_interval", self.check_interval)
        self.active_checks_enabled = config.get("active_checks_enabled", True)
        self.checks = config.get("checks", [])

    def __getitem__(self, key):
        return self.__getattribute__(key)

    def __repr__(self):
        r = "<Instance 'name': '%s', 'register': %s, 'address': '%s'>" % (
            self.name, self.register, self.address)
        return r

    def get(self, key, default=None):
        try:
            return self.__getattribute__(key)
        except AttributeError:
            return default


