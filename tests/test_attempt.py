from samm.attempt import Attempt
from samm.config import Config
from time import time

def test_attempt_up():
	config = Config('tests/etc/conf_valid.json')
	assert config.reload()
	a=Attempt(config, 'test_instance', 'test_check_up')
	a.schedule(0)
	b={}
	assert a.due()
	assert a.process(b)
	assert "test_instance" in b
	test_instance = b['test_instance']
	with open('tests/expected_attempt_metrics_up.txt', "r") as f:
		for metric_key in test_instance:
			expected_line = f.readline()
			assert expected_line == str(test_instance[metric_key])
	assert a.next_run > 0
	assert not a.due()
	a.schedule(-1)
	assert a.due()
	a.schedule(5)
	assert not a.due()

def test_attempt_down():
	config = Config('tests/etc/conf_valid.json')
	assert config.reload()
	a=Attempt(config, 'test_instance', 'test_check_down')
	a.schedule(0)
	b={}
	assert a.due()
	assert a.process(b)
	assert "test_instance" in b
	test_instance = b['test_instance']
	with open('tests/expected_attempt_metrics_down.txt', "r") as f:
		for metric_key in test_instance:
			expected_line = f.readline()
			assert expected_line == str(test_instance[metric_key])
	assert a.next_run > 0
	assert not a.due()
	a.schedule(-1)
	assert a.due()
	a.schedule(5)
	assert not a.due()

def test_attempt_check_up():
	config = Config('tests/etc/conf_valid.json')
	assert config.reload()
	a=Attempt(config, 'test_instance2', 'test_check_up')
	a.schedule(0)
	b={}
	assert a.due()
	assert a.process(b)
	assert "test_instance2" in b
	test_instance2 = b['test_instance2']
	with open('tests/expected_attempt_metrics_check_up.txt', "r") as f:
		for metric_key in test_instance2:
			expected_line = f.readline()
			assert expected_line == str(test_instance2[metric_key])
	assert a.next_run > 0
	assert not a.due()
	a.schedule(-1)
	assert a.due()
	a.schedule(5)
	assert not a.due()
