# Prepare grafana files
* Request certificate and store it in grafana folder
* edit conf/grafana.ini and set the path for certificate and key in cert_file and cert_key
* configure authentication (if google use https://grafana.com/docs/grafana/latest/setup-grafana/configure-security/configure-authentication/google/)
* certificate is mandatory for google authentication
* edit the file at conf/provisioning/datasources/samm-prometheus.yaml and set the IP address of the prometheus server. If mapping ports to host, use the host IP address and mapped port
# Start grafana container
`./create-container.sh <path to config>
`

# Prepare config
`PROMIP=$(docker inspect prometheus | jq -r ".[0].NetworkSettings.IPAddress")
mkdir -p /usr/local/samm/grafana
cp -R conf /usr/local/samm/grafana

sed -i -e "s/%PROMIP%/$PROMIP/" /usr/local/samm/grafana/conf/provisioning/datasources/samm-prometheus.yaml
`
