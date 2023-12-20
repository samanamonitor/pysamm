import sys, requests, json
from time import time, process_time
import logging

log = logging.getLogger(__name__)

class LokiStream:
    def __init__(self, submodule_str, loki_url, tags={}, tag_property={}, time_property=None, **kwargs):
        mod_str, _sep, class_str = submodule_str.rpartition('.')
        __import__(mod_str)
        iterable_class = getattr(sys.modules[mod_str], class_str)
        self.tag_property = tag_property
        self.iterable = iterable_class(**kwargs)
        self.initialized = False
        self.values = []
        self.time_property = time_property
        self.tags = tags
        self.loki_url = loki_url
        self.metrics = {
            'ls_events': 0,
            'ls_pull_process_time': 0,
            'ls_push_process_time': 0,
        }

    def set_tags(self, item):
        self.initialized = True
        for key, prop in self.tag_property.items():
            self.tags[key] = item[prop]

    def pull(self):
        self.values = []
        s = process_time()
        for item in self.iterable:
            if not self.initialized:
                self.set_tags(item)
            event_time = int(item.get(self.time_property, time()) * 1000000000)
            self.values += [[ str(event_time), json.dumps(dict(item)) ]]
        self.metrics['ls_pull_process_time'] = process_time() - s
        self.metrics['ls_events'] = len(self.values)

    def push(self):
        if self.metrics['ls_events'] == 0:
            self.metrics['ls_push_process_time'] = 0
            return
        s = process_time()
        headers = {
            'Content-type': 'application/json'
        }
        payload = {
            'streams': [ ]
        }
        payload['streams'] += [ {
            'stream': self.tags,
            'values': self.values
        }]
        p = json.dumps(payload)
        log.debug(p)
        self.answer = requests.post(self.loki_url, data=p, headers=headers)
        log.debug(self.answer.text)
        self.metrics['ls_push_process_time'] = process_time() - s

    def __iter__(self):
        self.pull()
        self.push()
        self._sent = 0
        return self

    def __next__(self):
        if self._sent:
            raise StopIteration
        self._sent = 1
        return { **self.metrics, **self.tags }
