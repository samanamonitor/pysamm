class DummyModule:
	def __iter__(self):
		return iter(self.data)


class DummyModuleUp(DummyModule):
	def __init__(self, *args, **kwargs):
		self.data = [ 
		{ "name": "item1", "metric1": 1, "metric2": 10}, 
		{ "name": "item2", "metric1": 2, "metric2": 20}, 
		{ "name": "item3", "metric1": 3, "metric2": 30} ]

class DummyModuleDown(DummyModule):
	def __init__(self, *args, **kwargs):
		self.data = []
