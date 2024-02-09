from .sammobject import SammObject, SammException
from .check import Check

class Instance(SammObject):
	def __init__(self, object_definition, configuration=None):
		super(Instance, self).__init__(object_definition, configuration)

	def pre_process(self):
		'''
		Sets all variables defined in object definition
		'''
		super(Instance, self).pre_process()
		self._config_section = "instances"
		self.up_check_name = None
		self.up_metric_name = None
		self.is_alive = 0
		self._checks = {}

	def _set_defaults(self):
		_ = self._attributes.setdefault("alias", self.name)
		_ = self._attributes.setdefault("display_name", self.name)
		_ = self._attributes.setdefault("address", None)
		_ = self._attributes.setdefault("checks", [])
		_ = self._attributes.setdefault("check_if_down", True)
		_ = self._attributes.setdefault("up_check", None)

	def post_process(self):
		'''
		Resoves all links with checks
		'''
		super(Instance, self).post_process()
		self._set_defaults()
		for check_name in self._attributes['checks']:
			check = self._config.get(("checks", check_name))
			if not isinstance(check, Check):
				raise SammException("Invalid check %s defined in instance %s" %
					(check_name, self.name))
			check.post_process()
			self._checks[check_name] = check
		if isinstance(self.up_check, str):
			self.up_check_name, _sep, self.up_metric_name = self.up_check.rpartition('.')
		self._applied_templates = True

	@property
	def __dict__(self):
		output = super(Instance, self).__dict__
		for check_name, check in self._checks.items():
			output.setdefault('_checks', {})[check_name] = check.__dict__
		output['up_check_name'] = self.up_check_name
		output['up_metric_name'] = self.up_metric_name
		return output
