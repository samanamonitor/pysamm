#!/usr/bin/python3
from samm.collector import Collector
import sys
import os
import logging

log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)

if __name__ == '__main__':
	if len(sys.argv) != 2:
		logging.exception(sys.argv)
		raise TypeError("Usage: {sys.argv[0]} <config file>")
	try:
		config_file = sys.argv[1]
		collector = Collector(config_file)
		collector.run()
	except KeyboardInterrupt:
		try:
			sys.exit(0)
		except SystemExit:
			os._exit(0)