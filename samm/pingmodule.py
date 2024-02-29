from icmplib import ping, NameLookupError, DestinationUnreachable, TimeExceeded
import logging

log = logging.getLogger(__name__)

class PingModule:
	def __init__(self, hostaddress, **kwargs):
		self.hostaddress = hostaddress
		ping_args = [ "count", "interval", "timeout", "id", "source", 
			"family", "privileged", "payload", "payload_size", 
			"traffic_class" ]
		self.kwargs = {}
		for k in kwargs:
			if k in ping_args:
				self.kwargs[k] = kwargs[k]

	def __iter__(self):
		data = {
			'hostaddress': self.hostaddress,
			'address': 'dnsfail',
			'min_rtt': 0,
			'avg_rtt': 0,
			'max_rtt': 0,
			'packets_sent': 0,
			'packets_received': 0,
			'is_alive': False
		}
		try:
			p = ping(self.hostaddress, **self.kwargs)
			data['address'] = p.address
			data['min_rtt'] = p.min_rtt
			data['avg_rtt'] = p.avg_rtt
			data['max_rtt'] = p.max_rtt
			data['packets_sent'] = p.packets_sent
			data['packets_received'] = p.packets_received
			data['is_alive'] = int(p.is_alive)
		except NameLookupError:
			data['address'] = 'dnsfail'
		except DestinationUnreachable:
			data['address'] = 'unreachable'
		except TimeExceeded:
			data['address'] = 'timeexceeded'
		except Exception as e:
			log.exception(e)
			data['address'] = 'unknownerror'
		return iter([data])

	def __next__(self):
		raise StopIteration

