#!/bin/bash

dataset="RefSet5"
GODBname="ServerIndexed.db"
DBpath=$( echo "ReadProgram('lib/darwinit'): eval( symbol(lowercase('$dataset').'DBpath') );" | darwin -q -B)

BINDIR="$DARWIN_BROWSER_REPO_PATH/data/UpdateGO/bin"
LIBDIR="$DARWIN_BROWSER_REPO_PATH/data/UpdateGO/lib"

java -cp $BINDIR:$LIBDIR/mysql-connector-java-5.1.13-bin.jar:$LIBDIR/commons-net-3.1.jar ch.ethz.cbrg.UpdateGO $DBpath




