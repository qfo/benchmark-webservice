#!/bin/bash

ulimit -s unlimited
ROOT="/local/BenchmarkService"
/usr/bin/nohup /local/bin/darwin64 -i $ROOT/ServerMain.drw >> $ROOT/output &
