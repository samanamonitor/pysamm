#!/usr/bin/python3

import yaml, sys

config=None

if len(sys.argv) < 3:
    raise TypeError("Invalid number of parameters. Expecting 2")

config_file=sys.argv[1]
new_target=sys.argv[2]

with open(config_file, "r") as f:
    config=yaml.safe_load(f)

samm_sc = None
for sc in config['scrape_configs']:
    if "job_name" in sc and sc["job_name"] == "samm":
        samm_sc = sc
        break

if samm_sc is None:
    samm_sc = { 
        "job_name": "samm",
        "honor_labels": True,
        "static_configs": []
        }

if not isinstance(samm_sc.get("static_configs", None), list):
    samm_sc["static_configs"] = []
samm_sc = samm_sc["static_configs"]


for o in samm_sc:
    for t in o["targets"]:
        if t == new_target:
            print("Target is already configured")
            exit(0)

samm_sc += [ { "targets": [ new_target ] } ]

print(yaml.safe_dump(config))
