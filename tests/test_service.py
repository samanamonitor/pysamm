from samm.service import Service
from socket import socket

def test_service():
	s=Service('tests/etc/conf_valid.json')
	assert len(s.attempt_list) == 4
	assert len(s.metric_data) == 3
	assert ['samm_service', 'test_instance', 'test_instance2'] == list(s.metric_data.keys())
	assert len(s.metric_data['samm_service']) == 8
	assert isinstance(s.sock, socket)
	assert list(s.tags.keys()) == ['instance', 'job']
