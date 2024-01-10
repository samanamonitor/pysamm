from samm.config import Config
import json

config = None

def test_01_load_config():
    global config
    config = Config("tests/etc/conf_ldap_discovery.json")
    assert isinstance(config, Config)

def test_02_reload():
    assert config.reload()

def test03_config_valid():
    with open('tests/expected_config_ldap_discovery.json') as f:
        expected = json.load(f)
    assert expected == config.__dict__

#def test_03_inheritance_test_instace():
#    i = config.get("instances.test_instance")
#    assert isinstance(i, instance)
#    result = i.dict()
#    with open("tests/expected_config_template_test_instance.txt", "r") as f:
#        expected = json.load(f)
#    assert result == expected
#
#def test_04_inheritance_template_other():
#    i = config.get("instances.template_other")
#    assert isinstance(i, instance)
#    result = i.dict()
#    with open("tests/expected_config_template_other.txt", "r") as f:
#        expected = json.load(f)
#    assert result == expected
#
#def test_05_inheritance_template_host():
#    i = config.get("instances.template_host")
#    assert isinstance(i, instance)
#    result = i.dict()
#    with open("tests/expected_config_template_host.txt", "r") as f:
#        expected = json.load(f)
#    assert result == expected
#
#