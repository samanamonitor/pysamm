from samm.config import Config
import json

config = None

def test_01_load_config():
	global config
	config = Config("tests/etc/conf_ldap_discovery3.json")
	assert isinstance(config, Config)

def test_02_reload():
	assert config.reload()

def test03_config_valid():
	with open('tests/expected_config_ldap_discovery3.json') as f:
		expected = json.load(f)
	assert config.__dict__ == expected
