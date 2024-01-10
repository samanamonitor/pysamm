from .sammobject import SammObject, SammException

class Check(SammObject):
    def __init__(self, config, configuration=None):
        super(Check, self).__init__(config, configuration)
        self._config_section = "checks"
        self._command = None

    def _post_process_internal(self):
        command_name = self._attributes['command']
        command = self._config.get(("commands", command_name))
        if command is None:
            raise SammException("Command %s defined in check %s doesn't exist" % 
                (self.command, self.name))
        command.post_process()
        self._command = command

    def dict(self):
        output = self._attributes.copy()
        output['_command'] = self._command.dict()
        output['register'] = self.register
        return output