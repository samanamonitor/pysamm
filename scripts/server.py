#!/usr/bin/python3
import sys, os
from sys import argv
from samm.service import Service
import time
import logging
import warnings

logging.basicConfig(stream=sys.stderr, level="WARNING")
log = logging.getLogger(__name__)

svc = None

def main(config_file):
    global svc
    wait_on_error=0
    warnings.filterwarnings(action='ignore',module='sammwr.utils')
    try:
        svc = Service(config_file)
        wait_on_error = svc.running_config.get("wait_on_error", 0)
        svc.process_loop()
    except Exception as e:
        log.exception(e)
        time.sleep(wait_on_error)
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise TypeError("must define config file")
    main(sys.argv[1])
