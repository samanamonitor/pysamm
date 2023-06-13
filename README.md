# Build DEB package
`docker run -it -v $(pwd):/usr/src/build -w /usr/src/build --rm ubuntu:jammy support/build-deb.sh`

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