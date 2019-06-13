#!/bin/bash

type -a docker > /dev/null

if [ $? -ne 0 ] ; then
    echo "UNCONFIGURED: No docker executable" 1>&2
    exit 1
fi

tag_id="${1:-latest}"

for docker_name in qfo_darwin qfo_python ; do
    docker build -t "$docker_name":"$tag_id" -f "Dockerfile_${docker_name}" .
done
