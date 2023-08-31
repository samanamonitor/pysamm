from samm.config import Config
from json.decoder import JSONDecodeError
import pytest

def test_createobject():
	config = Config('')
	assert isinstance(config, Config)

def test_file_not_found():
	config = Config('filenotfound.json')
	with pytest.raises(FileNotFoundError):
		config.reload()

def test_invalid_syntax():
	config = Config('tests/etc/conf_invalid_syntax.json')
	with pytest.raises(JSONDecodeError):
		config.reload()

def test_invalid_base_dir1():
	config = Config('tests/etc/conf_invalid_base_dir1.json')
	with pytest.raises(KeyError):
		config.reload()

def test_invalid_base_dir2():
	config = Config('tests/etc/conf_invalid_base_dir2.json')
	with pytest.raises(FileNotFoundError):
		config.reload()

def test_invalid_config_dir1():
	config = Config('tests/etc/conf_invalid_config_dir1.json')
	with pytest.raises(KeyError):
		config.reload()

def test_invalid_config_dir2():
	config = Config('tests/etc/conf_invalid_config_dir2.json')
	with pytest.raises(FileNotFoundError):
		config.reload()

def test_invalid_resource1():
	config = Config('tests/etc/conf_invalid_resource1.json')
	with pytest.raises(KeyError):
		config.reload()

def test_invalid_resource2():
	config = Config('tests/etc/conf_invalid_resource2.json')
	with pytest.raises(FileNotFoundError):
		config.reload()

def test_invalid_objects1():
	config = Config('tests/etc/conf_invalid_objects1.json')
	with pytest.raises(TypeError):
		config.reload()

def test_invalid_objects2():
	config = Config('tests/etc/conf_invalid_objects2.json')
	with pytest.raises(FileNotFoundError):
		config.reload()

def test_invalid_objects3():
	config = Config('tests/etc/conf_invalid_objects3.json')
	with pytest.raises(TypeError):
		config.reload()

def test_invalid_objects4():
	config = Config('tests/etc/conf_invalid_objects4.json')
	with pytest.raises(JSONDecodeError):
		config.reload()

def test_invalid_objects5():
	config = Config('tests/etc/conf_invalid_objects5.json')
	with pytest.raises(TypeError):
		config.reload()

def test_invalid_objects6():
	config = Config('tests/etc/conf_invalid_objects6.json')
	with pytest.raises(TypeError):
		config.reload()

def test_invalid_objects7():
	config = Config('tests/etc/conf_invalid_objects7.json')
	with pytest.raises(KeyError):
		config.reload()

def test_invalid_objects8():
	config = Config('tests/etc/conf_invalid_objects8.json')
	with pytest.raises(KeyError):
		config.reload()
