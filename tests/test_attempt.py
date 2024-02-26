from samm.attempt import Attempt
from samm.config import Config
from time import time, sleep

def test_attempt_up():
	config = Config('tests/etc/conf_valid.json')
	assert config.reload()
	instance_metric_data={}
	a=Attempt(config, 'test_instance', 'test_check_up', instance_metric_data)
	a.schedule(0)
	assert a.due()
	assert a.process()
	with open('tests/expected_attempt_metrics_up.txt', "r") as f:
		for metric_key, metric_value in instance_metric_data.items():
			expected_line = f.readline()
			assert expected_line == str(metric_value)
	sleep(.1)
	assert a.next_run > 0
	assert not a.due()
	a.schedule(-1)
	assert a.due()
	a.schedule(5)
	assert not a.due()

def test_attempt_down():
	config = Config('tests/etc/conf_valid.json')
	assert config.reload()
	instance_metric_data={}
	a=Attempt(config, 'test_instance', 'test_check_down', instance_metric_data)
	a.schedule(0)
	assert a.due()
	assert a.process()
	with open('tests/expected_attempt_metrics_down.txt', "r") as f:
		for metric_key, metric_value in instance_metric_data.items():
			expected_line = f.readline()
			assert expected_line == str(metric_value)
	assert a.next_run > 0
	assert not a.due()
	a.schedule(-1)
	assert a.due()
	a.schedule(5)
	assert not a.due()

def test_attempt_check_up():
	config = Config('tests/etc/conf_valid.json')
	assert config.reload()
	instance_metric_data={}
	a=Attempt(config, 'test_instance2', 'test_check_up', instance_metric_data)
	a.schedule(0)
	assert a.due()
	assert a.process()
	with open('tests/expected_attempt_metrics_check_up.txt', "r") as f:
		for metric_key, metric_value in instance_metric_data.items():
			expected_line = f.readline()
			assert expected_line == str(metric_value)
	assert a.next_run > 0
	assert not a.due()
	a.schedule(-1)
	assert a.due()
	a.schedule(5)
	assert not a.due()
