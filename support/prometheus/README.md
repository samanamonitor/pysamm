# Prepare prometheus files
* edit prometheus.yml file and set server targets for each samm-server running
* if data persistence is necessary, use a volume for /prometheus folder
# Start prometheus container
`sudo chmod o+rw /var/run/docker.sock
PROMETHEUS_CONFIG=/usr/local/samm/prometheus/prometheus.yml
docker run -d -v $PROMETHEUS_CONFIG:/etc/prometheus/prometheus.yml -v /var/run/docker.sock:/var/run/docker.sock -p 9090:9090 --name=prometheus prom/prometheus`