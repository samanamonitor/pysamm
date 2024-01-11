import logging

log = logging.getLogger(__name__)

try:
	from .check import Check as check
except Exception as e:
	log.exception(e)

try:
	from .command import Command as command
except Exception as e:
	log.exception(e)

try:
	from .discovery import Discovery as discovery
except Exception as e:
	log.exception(e)

try:
	from .instance import Instance as instance
except Exception as e:
	log.exception(e)

