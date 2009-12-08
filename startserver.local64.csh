#!/bin/csh
unlimit stacksize
/usr/bin/nohup /local/darwin_source/darwin64 </local/BenchmarkService/ServerMain.drw >>/local/BenchmarkService/output&
