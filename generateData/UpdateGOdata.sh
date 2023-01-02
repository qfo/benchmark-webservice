#!/bin/bash

GODBname="ServerIndexed.db"
DBpath="${QFO_REFSET_PATH}"

$DARWIN_BROWSER_REPO_PATH/data/UpdateGO/run.sh \
	-db $DBpath/$GODBname \
	-id $DBpath/IDIndex.db \
	-out $DBpath/${GODBname}.new \
        -go_annos "/scratch/aaltenho/go-release-reference/data/" \
	-genomes $DARWIN_GENOMES_PATH/species.txt

