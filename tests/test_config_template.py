from samm.config import Config
from samm.objecttype import instance
import json

config = None

def test_01_load_config():
	global config
	config = Config("tests/etc/conf_valid_template.json")
	assert isinstance(config, Config)

def test_02_reload():
	assert config.reload()

def test_03_inheritance_test_instace():
	i = config.get("instances.test_instance")
	assert isinstance(i, instance)
	result = i.__dict__
	with open("tests/expected_config_template_test_instance.txt", "r") as f:
		expected = json.load(f)
	assert result == expected

def test_04_inheritance_template_other():
	i = config.get("instances.template_other")
	assert isinstance(i, instance)
	result = i.__dict__
	with open("tests/expected_config_template_other.txt", "r") as f:
		expected = json.load(f)
	assert result == expected

def test_05_inheritance_template_host():
	i = config.get("instances.template_host")
	assert isinstance(i, instance)
	result = i.__dict__
	with open("tests/expected_config_template_host.txt", "r") as f:
		expected = json.load(f)
	assert result == expected

