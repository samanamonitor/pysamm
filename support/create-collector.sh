#!/bin/bash

set -ex

SAMM_BASE=$1
SAMM_CONF=${SAMM_BASE}/conf.json
IMAGE_NAME=samm-server

if [ -z "${SAMM_BASE}" ]; then
    echo "usage: $0 <path to samm configuration>" >&2
    exit 1
fi

if [ ! -d ${SAMM_BASE} ]; then
    echo "Path ${SAMM_BASE} doesn't exist. Cannot create collector" >&2
    exit 1
fi

if [ ! -f ${SAMM_CONF} ]; then
    echo "File ${SAMM_CONF} doesn't exist. Cannot create collector" >&2
    exit 1
fi

SAMM_NAME=$(cat ${SAMM_CONF} | jq -r .tags.job 2>/dev/null)
if [ "$?" != 0 ]; then
    echo "Invalid configuration file ${SAMM_CONF}. Cannot create collector" >&2
    exit 1
fi

docker run -idt --name ${SAMM_NAME} \
    -v $SAMM_BASE:/usr/local/samm/etc \
    -v /usr/share/snmp:/usr/share/snmp \
    --label samm=collector \
    --restart unless-stopped \
    ${IMAGE_NAME}:latest \
    /usr/local/samm/etc/conf.json