import re, os, json, sys
from .instance import Instance

class Config():
    def __init__(self, config_file):
        self.config_file = config_file
        self.modules = {}
        self.reload()

    def reload(self):
        with open(self.config_file) as f:
            self._config = json.load(f)
        if "resource_file" not in self._config:
            raise TypeError("missing resource_file")
        self.resource_file_path = self._config['base_dir'] + "/" + self._config['config_dir'] + "/" + self._config['resource_file']
        with open(self.resource_file_path) as f:
            self._config["resources"] = json.load(f)
        self._config["commands"] = {}
        self._config["checks"] = {}
        self._config["instances"] = {}
        for c in self._config['object_files']:
            object_file_path = self._config['base_dir'] + "/" + self._config['config_dir'] + "/" + c
            self.load(object_file_path)

    def load(self, filename):
        c=""
        with open(filename) as f:
            c=json.load(f)
        if not isinstance(c, list):
            raise TypeError("Invalid config type. Must be list")
        for o in c:
            if not isinstance(o, dict):
                raise TypeError("Invalid config type. data=%s" % str(o))
            if "object_type" not in o:
                raise TypeError("Invalid object_type. data=%s" % str(o))
            if "name" not in o:
                raise TypeError("Invalid object data. data=%s" % str(o))
            if o["object_type"] == "command":
                self._config["commands"][o["name"]] = o
            elif o["object_type"] == "check":
                self._config["checks"][o["name"]] = o
            elif o["object_type"] == "instance":
                self._config["instances"][o["name"]] = Instance(o)
            elif o["object_type"] == "check_group":
                self._config["check_groups"][o["name"]] = o

    def get(self, in_data, instance_name=None, check_name=None, resolve_vars=False, default=None):
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

        return self.replace_vars(curconfig, instance_name=instance_name, check_name=check_name)

    def replace_vars(self, o, instance_name=None, check_name=None):
        out=None
        if isinstance(o, str):
            variables=self._get_variables(o)
            out=o
            for v in variables:
                var_value=self.get(v, instance_name=instance_name, check_name=check_name, resolve_vars=True)
                if isinstance(o, str) and isinstance(var_value, str):
                    out=o.replace("$(%s)" % v, var_value)
        elif isinstance(o, list):
            out = [None] + len(o)
            for i in range(len(o)):
                out[i] = self.replace_vars(o[i], instance_name=instance_name, check_name=check_name)
        elif isinstance(o, dict):
            out = {}
            for i in o:
                out[i] = self.replace_vars(o[i], instance_name=instance_name, check_name=check_name)
        return out

    def _get_variables(self, s):
        var_regex=r'(?<!\\)\$\(([^\)]+)\)'
        varlist=re.findall(var_regex, s)
        return varlist

    def run_module(self, module_str, **kwargs):
        if module_str not in self.modules:
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
            raise ImportError('Class %s cannot be found (%s)' %
                              (class_str,
                               traceback.format_exception(*sys.exc_info())))

