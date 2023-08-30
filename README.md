# Build DEB package
`docker run -it --rm -v $(pwd):/usr/src samm-repo /usr/local/bin/build-deb.sh`

# Upload to repo
docker run --rm -it -v $(pwd):/usr/src -w /usr/src samm-repo /usr/local/bin/add-file-repo.sh samm-pysamm_<version>-1_amd64.deb jammy

# Build SAMM container image
`cd support
docker build -t samm-server samm-server`

# Run SAMM container
## Copy configuration files and then edit them
`sudo mkdir -p /usr/local/samm/etc
sudo cp tests/conf.json.example /usr/local/samm/etc/conf.json
sudo cp tests/resources.json.example /usr/local/samm/etc/resources.json
sudo mkdir -p /usr/local/samm/etc/objects
sudo cp tests/objects/objects.json.example /usr/local/samm/etc/objects/objects.json
sudo mkdir -p /usr/local/samm/var`
## Run the container
`docker run -idt -v /usr/local/samm:/usr/local/samm --name samm-server samm-server /usr/local/samm/etc/conf.json`

# Run SAMM with flask
`export FLASK_APP=/usr/local/bin/metrics`
`flask run --host 0.0.0.0`
