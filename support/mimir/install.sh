#!/bin/bash

set -xe

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

usage() {
	echo $1 >&2
	echo "Usage: $0 <installation path>" >&2
	exit 1
}

INSTALL_PATH=$1
if [ -z "${INSTALL_PATH}" ]; then
	usage "ERROR: Please provide a file path"
fi

if [ -d "${INSTALL_PATH}" ]; then
	usage "ERROR: ${INSTALL_PATH} already exists. Remove the path before running this command again."
fi

CONTAINER_NAME=$2
if [ -z "${CONTAINER_NAME}" ]; then
	CONTAINER_NAME="samm-mimir"
fi

if [ ! -f "${DIR}/sammv2.env" ]; then
	usage "ERROR: Cannot continue without sammv2.env file"
fi

source ${DIR}/sammv2.env

if [ -n "${NOT_CONFIGURED}"
		|| -z "${AWS_SECRET_ACCESS_KEY}" 
		|| -z "${AWS_ACCESS_KEY_ID}" 
		|| -z "${SAMM_CUSTOMER}" ]; then
	usage "ERROR: To continue, customize the file sammv2.env and delete the variable NOT_CONFIGURED"
fi

mkdir -p ${INSTALL_PATH}
cp sammv2.env sammv2.yaml ${INSTALL_PATH}

MIMIR_CONTAINER=$(docker ps --filter name=sammvcenter -q)
if [ -n "${MIMIR_CONTAINER}" ]; then
	usage "ERROR: Container already exists. Remove the container before running this command again."
fi

docker run \
  --rm \
  --name samm-mimir \
  --publish 9009:9009 \
  --volume ${INSTALL_PATH}/sammv2.yaml:/etc/mimir/sammv2.yaml grafana/mimir:latest \
  --env-file ${INSTALL_PATH}/sammv2.env \
  --config.file=/etc/mimir/sammv2.yaml
