from .sammobject import SammObject

class Command(SammObject):
	def __init__(self, object_definition, configuration=None):
		super(Command, self).__init__(object_definition, configuration)

	def pre_process(self):
		super(Command, self).pre_process()
		self._config_section = "commands"

	def post_process(self):
		super(Command, self).post_process()
		self._applied_templates = True
