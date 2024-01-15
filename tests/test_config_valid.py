from samm.config import Config
import json

config = None

def test_01_load_config():
	global config
	config = Config("tests/etc/conf_valid.json")
	assert isinstance(config, Config)

def test_02_reload():
	assert config.reload()

def test_03_get_types():
	assert isinstance(config.get("webserver"), bool)
	assert isinstance(config.get("webserver_port"), int)
	assert isinstance(config.get("resource_file"), str)
	assert isinstance(config.get("object_files"), list)
	assert isinstance(config.get("tags"), dict)


def test_04_get_recurrent():
	assert config.get("tags.job") == "samm_job"
	assert config.get("instances.test_instance.alias") == "test_instance_alias"
	assert config.get(("instances", "test_instance", "alias")) == "test_instance_alias"

def test_05_get_variables():
	with open('tests/variable_strings.txt', "r") as f:
		data = json.load(f)
	for t in data:
		assert config.get_variables(t['text']) == eval(t['eval'])

def test_06_replace_vars():
	assert "test_address" == config.get('commands.test_command_up.args.address', \
		instance_name="test_instance", check_name="test_check_up", resolve_vars=True)
	assert ['metric1', 'metric2'] == config.get('commands.test_command_up.args.metrics', \
		instance_name="test_instance", check_name="test_check_up", resolve_vars=True)
	assert 2 == config.get('commands.test_command_up.args.numeric', \
		instance_name="test_instance", check_name="test_check_up", resolve_vars=True)
	assert "test_instance_alias_2" == config.get('instances.test_instance2.alias', resolve_vars=True)
