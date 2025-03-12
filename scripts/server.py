#!/usr/bin/python3
import sys, os
from sys import argv
from samm.service import Service
import time
from multiprocessing import Process
from flask import Flask, make_response
import socket
import logging
import warnings

app = Flask(__name__)
logging.basicConfig(stream=sys.stderr)

svc = None

@app.route('/metrics')
def metrics():
    global svc
    address = os.path.join(svc.running_config.get('base_dir'), svc.running_config.get("sock_file"))
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(address)
    s.send(b'\n')
    data = ""
    while True:
        newdata = s.recv(1024).decode('ascii')
        if len(newdata) == 0:
            break
        data += newdata

    s.close()
    res = make_response(data, 200)
    res.mimetype = "text/plain"
    return res

def web(port=5000):
    app.run(host='0.0.0.0', port=port)

def main(config_file):
    global svc
    wait_on_error=0
    samm_debug = os.getenv("SAMM_DEBUG")
    debug_modules = samm_debug.split(',')
    for module in debug_modules:
        l = logging.getLogger(module)
        l.setLevel("DEBUG")
    warnings.filterwarnings(action='ignore',module='sammwr.utils')
    try:
        svc = Service(config_file)
        wait_on_error = svc.running_config.get("wait_on_error", 0)
        if svc.running_config.get("webserver", False):
            port = svc.running_config.get("webserver_port", 5000)
            p = Process(target=web, args=(port,))
            p.start()
        svc.process_loop()
        p.terminate()
    except Exception as e:
        print(e)
        time.sleep(wait_on_error)
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise TypeError("must define config file")
    main(sys.argv[1])
