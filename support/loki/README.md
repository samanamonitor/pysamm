# Install

`
mkdir -p /usr/local/samm/loki
cp local-config.yaml /usr/local/samm/loki
docker run -idt -p 3100:3100 --name samm-loki -v /usr/local/samm/loki/local-config.yaml:/etc/loki/local-config.yaml grafana/loki`