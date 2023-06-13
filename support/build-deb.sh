#!/bin/bash

set -xe

. /etc/os-release

TEMPDIR=/usr/src/build

apt update
DEBIAN_FRONTEND="noninteractive" apt install -y python3-setuptools

python3 setup.py build
python3 setup.py bdist

tarball_path=$(find dist -type f -name \*.tar.gz)
tarball=$(basename ${tarball_path})

t=${tarball%.linux-x86_64.tar.gz}
VERSION=${t#*-}
PACKAGE_NAME=${t%-*}
PACKAGE_NAME=${PACKAGE_NAME/_/-}

BUILD_DIR=/usr/src/${PACKAGE_NAME}_${VERSION}-1_amd64
mkdir -p ${BUILD_DIR}/DEBIAN
cp ${TEMPDIR}/debian/control ${BUILD_DIR}/DEBIAN

tar -C ${BUILD_DIR} -xzvf ${tarball_path}

dpkg --build ${BUILD_DIR}

mv /usr/src/${PACKAGE_NAME}_${VERSION}-1_amd64.deb ${TEMPDIR}
