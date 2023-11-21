#!/bin/bash

type -a docker > /dev/null

if [ $? -ne 0 ] ; then
    echo "UNCONFIGURED: No docker executable" 1>&2
    exit 1
fi

tag_id="${1:-latest}"

docker build -t "qfobenchmark/python":"$tag_id" -f "Dockerfile_qfo_python" .
docker build -t "qfobenchmark/darwin":"$tag_id" -f "Dockerfile_qfo_darwin" .
docker build -t "qfobenchmark/fas_benchmark":"$tag_id" -f "Dockerfile_qfo_fas" .

