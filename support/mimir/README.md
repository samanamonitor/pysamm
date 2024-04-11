`docker run \
  --rm \
  --name samm-mimir \
  --publish 9009:9009 \
  --volume "$(pwd)"/sammv2.yaml:/etc/mimir/sammv2.yaml grafana/mimir:latest \
  --env-file sammv2.env \
  --config.file=/etc/mimir/sammv2.yaml`