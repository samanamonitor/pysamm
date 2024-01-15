from .sammobject import SammObject, SammException

class Check(SammObject):
	def __init__(self, config, configuration=None):
		super(Check, self).__init__(config, configuration)

	def pre_process(self):
		super(Check, self).pre_process()
		self._config_section = "checks"
		self._command = None

	def post_process(self):
		super(Check, self).post_process()
		command_name = self._attributes['command']
		command = self._config.get(("commands", command_name))
		if command is None:
			raise SammException("Command %s defined in check %s doesn't exist" % 
				(self.command, self.name))
		command.post_process()
		self._command = command
		self._applied_templates = True

	@property
	def __dict__(self):
		output = super(Check, self).__dict__
		output['_command'] = self._command.__dict__
		return output