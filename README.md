# TODO: update to the following versions for kerberos to work
# pykerberos        1.2.4
# requests-kerberos 0.14.0

# Test json files
`for i in $(ls -1 *.json); do cat $i | jq > /dev/null || echo "error on $i"; done`

# Build DEB package
`docker run -it --rm -v $(pwd):/usr/src sammrepo /usr/local/bin/build-deb.sh`

# Upload to repo
`package=<package deb file>
arch=<architecture name arm64 or amd64>
docker run --rm -it -v $(pwd):/usr/src -v $(pwd)/../gpg:/gpg -v ~/.aws:/root/.aws -w /usr/src sammrepo /usr/local/bin/add-file-repo.sh $package jammy $arch`

# Build SAMM container image
`cd support
VERSION=x.x.x.x
docker build --no-cache -t samm-server:$VERSION samm-server`

# Install Docker
## Redhat
https://help.hcltechsw.com/bigfix/10.0/mcm/MCM/Install/install_docker_ce_docker_compose_on_rhel_8.html
## Other Linux
https://docs.docker.com/engine/install/

## After installation
`
sudo -s
if ! grep -q '\-H tcp://172.17.0.1:2375'  /lib/systemd/system/docker.service; then
	sudo sed -i -e 's|\(ExecStart=/usr/bin/dockerd -H fd://.*\)|\1  -H tcp://172.17.0.1:2375|' /lib/systemd/system/docker.service
	sudo systemctl daemon-reload
	sudo systemctl restart docker
fi`

# Run SAMM container
## Copy configuration files and then edit them
`sudo mkdir -p /usr/local/samm/etc
sudo cp docs/examples/conf.json.example /usr/local/samm/etc/conf.json
sudo cp docs/examples/resources.json.example /usr/local/samm/etc/resources.json
sudo mkdir -p /usr/local/samm/etc/objects
sudo cp docs/examples/objects/* /usr/local/samm/etc/objects/
sudo mkdir -p /usr/local/samm/var`

## Run the container
`SAMM_PATH=/usr/local/samm/samm
docker run -idt -v $SAMM_PATH:/usr/local/samm/etc --name samm-server --label samm=collector --restart unless-stopped samm-server /usr/local/samm/etc/conf.json`

# To run unit tests
## python3-pytest must be installed
`python3 -m pytest`

# TODO
* procedure to install new MIB
* check MIB integrity


# Limits
After testing SAMM with lots of hosts, we found that it is best to configure less than 3500(190k metrics - 4seconds download) attempts per container. Having more than this number of attempts configured in a single container will cause the download of metrics from prometheus to take too long and it will give up, losing data. It is important to measure the time it takes to poll for the entire metric table from a container to establish how big it can get.

# Server install on Red Hat
`nmcli connection add type bridge con-name docker-local ifname docker-local stp no
nmcli connection modify docker-local connection.autoconnect yes
nmcli connection modify docker-local +ipv4.address "100.100.200.200/32"
nmcli con modify docker-local ipv4.method 'manual'
nmcli connection up docker-local
`

# Developer environment
`docker build --tag sammdev --no-cache .
docker run -it --rm -v $(pwd):/usr/src/pysamm sammdev
python3 -m pytest
`