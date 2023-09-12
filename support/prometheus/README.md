# Prepare prometheus files
* edit prometheus.yml file and set server targets for each samm-server running
* if data persistence is necessary, use a volume for /prometheus folder
# Start prometheus container
`docker run -d -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml -p 9090:9090 --name=prometheus prom/prometheus`