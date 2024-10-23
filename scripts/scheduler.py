#!/usr/bin/python3
from samm.scheduler import Scheduler
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
		scheduler = Scheduler(config_file)
		scheduler.run()
	except KeyboardInterrupt:
		try:
			sys.exit(0)
		except SystemExit:
			os._exit(0)