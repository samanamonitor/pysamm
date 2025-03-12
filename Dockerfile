FROM python:3.10
COPY dev-requirements.txt /tmp
RUN <<EOF
apt update
apt upgrade -y
apt install -y libsasl2-dev python-dev-is-python3 libldap2-dev libssl-dev
pip install -r /tmp/dev-requirements.txt
#rm -rf /var/lib/apt/lists/*
EOF
WORKDIR /usr/src/pysamm
ENTRYPOINT /bin/bash