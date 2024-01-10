from .sammobject import SammObject

class Command(SammObject):
    def __init__(self, object_definition, configuration=None):
        super(Command, self).__init__(object_definition, configuration)
        self._config_section = "commands"

    def dict(self):
        output = self._attributes.copy()
        output['register'] = self.register
        return output