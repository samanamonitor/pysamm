#!/bin/bash

LOCAL_PATH=$1
if [ ! -f  "${LOCAL_PATH}/grafana.db" ]; then
	touch ${LOCAL_PATH}/grafana.db
fi

mkdir -p ${LOCAL_PATH}/db
mkdir -p ${LOCAL_PATH}/plugins
mkdir -p ${LOCAL_PATH}/dashboards
touch ${LOCAL_PATH}/db/grafana.db

docker run -d \
	-v ${LOCAL_PATH}/plugins:/var/lib/grafana/plugins \
	-v ${LOCAL_PATH}/conf:/etc/grafana \
	-v ${LOCAL_PATH}/dashboards:/var/lib/grafana/dashboards \
	-p 3000:3000 --restart unless-stopped --name=grafana2 grafana/grafana-enterprise
