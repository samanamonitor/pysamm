#!/bin/bash

VERSION=$(PYTHONPATH=$(pwd)/.. python3 -c "import samm; print(samm.__version__)")
docker rmi samm-server:latest
docker build --no-cache -t samm-server:$VERSION -t samm-server:latest samm-server
