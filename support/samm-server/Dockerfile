FROM ubuntu:jammy
RUN <<EOF
KEYPATH=/var/lib/samana
KEYFILE=pgp-samm-key.public
DEBIAN_FRONTEND="noninteractive"
apt update
apt upgrade -y
apt install -y ca-certificates wget
mkdir -p ${KEYPATH}
wget -O ${KEYPATH}/${KEYFILE} https://samm-repo.s3.amazonaws.com/${KEYFILE}
echo "deb [arch=amd64 signed-by=${KEYPATH}/${KEYFILE}] https://samm-repo.s3.amazonaws.com jammy main" \
    > /etc/apt/sources.list.d/samm.list
apt update
apt install -y samm-pysamm samm-pysammwr
EOF
ENTRYPOINT [ "/usr/local/bin/server.py" ]
