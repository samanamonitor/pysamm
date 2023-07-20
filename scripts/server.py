#!/usr/bin/python3
import sys
from sys import argv
from samm.service import Service
import time

svc = None

def main(config_file):
    global svc
    try:
        svc = Service(config_file)
        svc.process_loop()
    except Exception as e:
        print(e)
        time.sleep(600)
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise TypeError("must define config file")
    main(sys.argv[1])
