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

# Run SAMM container
## Copy configuration files and then edit them
`sudo mkdir -p /usr/local/samm/etc
sudo cp tests/conf.json.example /usr/local/samm/etc/conf.json
sudo cp tests/resources.json.example /usr/local/samm/etc/resources.json
sudo mkdir -p /usr/local/samm/etc/objects
sudo cp tests/objects/objects.json.example /usr/local/samm/etc/objects/objects.json
sudo mkdir -p /usr/local/samm/var`

## Run the container
`SAMM_PATH=/usr/local/samm/samm1
docker run -idt -v $SAMM_PATH:/usr/local/samm/etc --name samm-server --label samm=collector samm-server /usr/local/samm/etc/conf.json`

# To run unit tests
## python3-pytest must be installed
`python3 -m pytest`

# TODO
* procedure to install new MIB
* check MIB integrity