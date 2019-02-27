#!/bin/bash

type -a docker > /dev/null

if [ $? -ne 0 ] ; then
	echo "UNCONFIGURED: No docker executable" 1>&2
	exit 1
fi

if [ $# -gt 0 ]; then
	tag_id="$1"

	for docker_name in qfo_darwin qfo_python ; do
		docker build -t "$docker_name":"$tag_id" -f "Dockerfile_${docker_name}" .
	done
else
	echo "Usage: $0 tag_id" 1>&2
	exit 1
fi
