#!/bin/bash

VERSION=$(PYTHONPATH=$(pwd)/.. python3 -c "import samm; print(samm.__version__)")
docker build --no-cache -t samm-server:$VERSION samm-server
