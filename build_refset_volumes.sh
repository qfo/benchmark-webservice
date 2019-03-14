#!/bin/bash

type -a docker > /dev/null

if [ $? -ne 0 ] ; then
	echo "UNCONFIGURED: No docker executable" 1>&2
	exit 1
fi

for year in 2011 2018 ; do
    VOL="refset$year"
    docker volume create $VOL
    docker run --rm -t -i --mount source=$VOL,target=/refset qfo_darwin:latest bash -c "cd /refset;
        curl -SL -O https://orthology.benchmarkservice.org/refsets/$year/Summaries.drw.gz;
        curl -SL -O https://orthology.benchmarkservice.org/refsets/$year/GOdata.drw.gz
        curl -SL -O https://orthology.benchmarkservice.org/refsets/$year/mapping.json.gz
        curl -SL -O https://orthology.benchmarkservice.org/refsets/$year/ServerIndexed.db
        curl -SL -O https://orthology.benchmarkservice.org/refsets/$year/ServerIndexed.db.map
        curl -SL -O https://orthology.benchmarkservice.org/refsets/$year/ServerIndexed.db.tree
        curl -SL -O https://orthology.benchmarkservice.org/refsets/$year/enzymes.drw.gz"
done





