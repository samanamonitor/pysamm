import sys
import os
import logging

log = logging.getLogger(__name__)

if __name__ == '__main__':
	if len(sys.argv) != 2:
		logging.exception(sys.argv)
		raise TypeError("Arguments must be <config file>")
	try:
		config_file = sys.argv[1]
		scheduler = Scheduler(config_file)
		scheduler.run()
	except KeyboardInterrupt:
		print('Interrupted')
		try:
			sys.exit(0)
		except SystemExit:
			os._exit(0)