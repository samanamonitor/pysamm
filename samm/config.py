import re, os, json, sys
from .objecttype import Instance, Command, Check

def get_variables(s):
    '''This function receives a string containing text and variables in the form $(variable_name)
    and will return a list of variable names. It can detect multiple variables.
    Variable names cannot contain the following characters (,),\\ or quotes
'''
    var_regex=r'(?<!\\)\$\(([^\)]+)\)'
    varlist=re.findall(var_regex, s)
    return varlist

def replace_vars(o, config, instance_name=None, check_name=None, default=None, default_variable=""):
    out=None
    if isinstance(o, str):
        '''
        We don't need to continue recursion. Just find variables and replace them
        '''
        variables=get_variables(o)
        out=o
        if not isinstance(default, str):
            defaut = ""
        for v in variables:
            var_value=config.get(v, instance_name=instance_name, check_name=check_name, resolve_vars=True, default=default)
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
            out[i] = replace_vars(o[i], config, instance_name=instance_name, check_name=check_name, default=default)
    elif isinstance(o, dict):
        '''
        We need to process recursively for each item in the dict
        '''
        out = {}
        for i in o:
            out[i] = replace_vars(o[i], config, instance_name=instance_name, check_name=check_name)
    else:
        out = default
    return out


class Config():
    def __init__(self, config_file):
        self._valid_config = False
        self.config_file = config_file
        self.modules = {}
        self._config = None

    def reload(self):
        with open(self.config_file) as f:
            self._config = json.load(f)

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
            self._config["resources"] = json.load(f)

        self._config["commands"] = {}
        self._config["checks"] = {}
        self._config["instances"] = {}

        object_files = self._config.get('object_files', [])
        if not isinstance(object_files, list):
            raise TypeError("object_files must be a list")
        for c in self._config['object_files']:
            object_file_path = os.path.join(self._config['config_dir'], c)
            self.load(object_file_path)

        _ = self._config.setdefault("tags", {}).setdefault("job", "samm")
        self._valid_config = True
        return self._valid_config


    def load(self, filename):
        c=None
        with open(filename) as f:
            c=json.load(f)
        if not isinstance(c, list):
            raise TypeError("Invalid config type. Must be list")
        for o in c:
            if not isinstance(o, dict):
                raise TypeError("Invalid config type. Expecting dict. data=%s" % str(o))
            if "object_type" not in o:
                raise KeyError("Mandatory \'object_type\' missing. data=%s" % str(o))
            if "name" not in o:
                raise KeyError("Mandatory \'name\' missing. data=%s" % str(o))
            if o["object_type"] == "command":
                self._config["commands"][o["name"]] = Command(o, self._config)
            elif o["object_type"] == "check":
                self._config["checks"][o["name"]] = Check(o, self._config)
            elif o["object_type"] == "instance":
                self._config["instances"][o["name"]] = Instance(o, self._config)

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

        return replace_vars(curconfig, self, instance_name=instance_name, check_name=check_name, default=default, default_variable=default_variable)

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

