#!/bin/bash

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

SAMM_BASE=/usr/local/samm
SAMM_ETC=${SAMM_BASE}/etc
PROMETHEUS_PATH=${SAMM_BASE}/prometheus
PROMETHEUS_TMPL=${DIR}/prometheus/prometheus.yml
PROMETHEUS_CFG=${PROMETHEUS_PATH}/prometheus.yml
SAMM_VAR=${SAMM_BASE}/var
SAMM_NAME=samm-server
IMAGE_NAME=samm-server
IMAGE_VERSION=latest

if [ ! -d "${SAMM_ETC}" ]; then
    sudo mkdir -p ${SAMM_ETC}
fi
if [ ! -d "${SAMM_ETC}"/objects ]; then
    sudo mkdir -p ${SAMM_ETC}/objects
fi
if [ ! -d "${SAMM_BASE}/var" ]; then
    sudo mkdir -p ${SAMM_BASE}/var
fi

docker build -t samm-server samm-server
sudo cp ../tests/conf.json.example ${SAMM_ETC}/conf.json
sudo cp ../tests/resources.json.example ${SAMM_ETC}/resources.json
sudo cp ../tests/objects/objects.json.example ${SAMM_ETC}/objects/objects.json
docker run -idt -v $SAMM_BASE:/usr/local/samm/etc --name ${SAMM_NAME} \
    -v /usr/share/snmp:/usr/local/share \
    --label samm=collector --restart unless-stopped ${IMAGE_NAME}:${IMAGE_VERSION} \
    /usr/local/samm/etc/conf.json

docker build -t samm-apache samm-apache
docker run -idt -p 9091:80 --name samm-apache -v ${SAMM_VAR}:${SAMM_VAR} samm-apache
SAMMAPACHE_IP=$(docker inspect samm | jq -r ".[0].NetworkSettings.IPAddress")

if [ ! -d "${PROMETHEUS_PATH}" ]; then
    mkdir -p ${PROMETHEUS_PATH}
fi
cp ${PROMETHEUS_TMPL} ${PROMETHEUS_CFG}
./add_prom_target.py ${PROMETHEUS_CFG} ${SAMMAPACHE_IP}:80 > ${PROMETHEUS_CFG}
docker run -idt -p 9090:9090 -v ${PROMETHEUS_CFG}:/etc/prometheus/prometheus.yml --name prometheus prom/prometheus

docker run -idt -p 3000:3000 --name grafana grafana/grafana-enterprise
