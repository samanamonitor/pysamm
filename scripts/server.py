#!/usr/bin/python3
import sys
from sys import argv
sys.path.append("..")
from samm.config import Config
from samm.attempt import Attempt
import os
from time import sleep, process_time
from random import Random
import socket, select

c=None
polltime=5
attempt_list = []
metric_data = {}
rand = Random()

def init_config(config_file):
    global c
    config_path, sep, config_file = config_file.rpartition("/")
    os.chdir(config_path)
    c=Config(config_file)

def init_attempts():
    global c, attempt_list
    instance_name="smnnovctxvda1"
    for check_name in c.get("instances." + instance_name + ".checks"):
        a = Attempt(c, instance_name, check_name)
        a.schedule(int(rand.gauss(5, 5)))
        attempt_list += [ a ]

def process_loop(s):
    global attempt_list, metric_data, polltime
    inputs = [ s ]
    while inputs:
        for a in attempt_list:
            if a.run(metric_data):
                a.schedule_next()
        print("Sleeping... %f" % process_time())
        c_read, c_write, in_error = select.select(inputs, [], [], polltime)
        for c in c_read:
            if c == s:
                connection, client_address = c.accept()
                for i in metric_data:
                    for k in metric_data[i]:
                        connection.sendall(("%s\n" % (metric_data[i][k])).encode('ascii'))
                connection.close()

def main(config_file):
    init_config(config_file)
    init_attempts()
    s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind("samm.sock")
    s.listen(1)
    process_loop(s)

        

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise TypeError("must define config file")
    main(sys.argv[1])
