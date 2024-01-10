from samm.utils import FilterFunction
import pytest

def test_valid_function():
	data={
			"objectClass": {
				"eq": "computer"
			},
			"lastLogonTimestamp": {
				"ge": {
					"Fn::adsecondsfromnow": [
						"31536000"
					]
				}
			}
		}
	result = FilterFunction.filter_dict_to_string(data)
	assert isinstance(result, str)
	assert result[:45] == '(&(objectClass=computer)(lastLogonTimestamp>='

def test_valid_single():
	data={
			"objectClass": {
				"eq": "computer"
			}
		}
	result = FilterFunction.filter_dict_to_string(data)
	assert isinstance(result, str)
	assert result == '(objectClass=computer)'

def test_valid_two():
	data={
			"objectClass": {
				"eq": "computer"
			},
			"other": {
				"ge": 2
			}
		}
	result = FilterFunction.filter_dict_to_string(data)
	assert isinstance(result, str)
	assert result == '(&(objectClass=computer)(other>=2))'

def test_valid_two():
	data={
			"objectClass": {
				"eq": "computer"
			},
			"other": {
				"ge": 2
			},
			"other2": {
				"eq": 3
			},
			"other3": {
				"le": 4
			},
			"other4": {
				"px": "asedf"
			}
		}
	result = FilterFunction.filter_dict_to_string(data)
	assert isinstance(result, str)
	assert result == '(&(objectClass=computer)(other>=2)(other2=3)(other3<=4)(other4~=asedf))'


def test_invalid_data():
	data=None
	with pytest.raises(TypeError):
		FilterFunction.filter_dict_to_string(data)

def test_invalid_dictionary_1():
	data = {}
	with pytest.raises(TypeError):
		result = FilterFunction.filter_dict_to_string(data)

def test_invalid_expression_1():
	data = {
		"test": 1
	}
	with pytest.raises(TypeError):
		result = FilterFunction.filter_dict_to_string(data)

def test_invalid_expression_2():
	data = {
		"test": {}
	}
	with pytest.raises(TypeError):
		result = FilterFunction.filter_dict_to_string(data)
	
def test_invalid_expression_3():
	data = {
		"test": {
			"asdf": 1
		}
	}
	with pytest.raises(TypeError):
		result = FilterFunction.filter_dict_to_string(data)

def test_invalid_function():
	data={
			"objectClass": {
				"eq": "computer"
			},
			"lastLogonTimestamp": {
				"ge": {
					"Fn::asdf": [
						"31536000"
					]
				}
			}
		}
	with pytest.raises(AttributeError):
		result = FilterFunction.filter_dict_to_string(data)

def test_invalid_function2():
	data={
			"objectClass": {
				"eq": "computer"
			},
			"lastLogonTimestamp": {
				"ge": {
					"Fn::": [
						"31536000"
					]
				}
			}
		}
	with pytest.raises(AttributeError):
		result = FilterFunction.filter_dict_to_string(data)

