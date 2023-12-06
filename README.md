# Build DEB package
`docker run -it --rm -v $(pwd):/usr/src sammrepo /usr/local/bin/build-deb.sh`

# Upload to repo
`package=<package deb file>
arch=<architecture name arm64 or amd64>
docker run --rm -it -v $(pwd):/usr/src -v $(pwd)/../gpg:/gpg -v ~/.aws:/root/.aws -w /usr/src sammrepo /usr/local/bin/add-file-repo.sh $package jammy $arch`

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
`docker run -idt -v /usr/local/samm/samm1:/usr/local/samm/etc --name samm-server -p 9091:5000 samm-server /usr/local/samm/etc/conf.json`

# Run SAMM with flask
`export FLASK_APP=/usr/local/bin/metrics`
`flask run --host 0.0.0.0`

# TODO
* procedure to install new MIB
* check MIB integrity