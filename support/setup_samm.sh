#!/bin/bash

PROMETHEUS_TMPL=/usr/src/sources/samanamonitor/pysamm/support/prometheus/prometheus.yml
PROMETHEUS_CFG=/usr/src/sources/samanamonitor/pysamm/support/prometheus.yml
SAMM_SOCK=/usr/src/sources/samanamonitor/pysamm/tests

docker build -t samm-apache samm-apache
docker run -idt -p 9091:80 --name samm -v ${SAMM_SOCK}:/usr/local/samm/var samm-apache
SAMM_IP=$(docker inspect samm | jq -r ".[0].NetworkSettings.IPAddress")
./add_prom_target.py ${PROMETHEUS_TMPL} ${SAMM_IP}:80 > ${PROMETHEUS_CFG}
docker run -idt -p 9090:9090 -v ${PROMETHEUS_CFG}:/etc/prometheus/prometheus.yml --name prometheus prom/prometheus
