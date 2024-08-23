#!/bin/bash

LOCAL_PATH=$1
if [ ! -f  "${LOCAL_PATH}/local-config.yaml" ]; then
	echo "Configuration file at ${LOCAL_PATH}/local-config.yaml not found."
	exit 1
fi

docker run -d \
	-v ${LOCAL_PATH}/local-config.yaml:/etc/loki/local-config.yaml  \
	-p 3100:3100 --name samm-loki \
	--restart unless-stopped grafana/loki
