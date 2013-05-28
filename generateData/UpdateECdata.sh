#!/bin/bash
darwin64="/local/bin/darwin64 -q"
enzRaw="/tmp/enzymes.dat"
enzDrw="/tmp/enzymes.drw"
dataset="RefSet5"
enzDat="data/enzymes_$dataset.drw"

wget "ftp://ftp.expasy.org/databases/enzyme/enzyme.dat" -O $enzRaw
if [ $? -ne 0 ] ; then echo "could not download enzyme.dat"; exit 1; fi

data/convert_ec.pl $enzRaw $enzDrw
if [ $? -ne 0 ] ; then echo "could not convert enzymes into darwin format"; exit 1; fi


$darwin64  << EOA
pwd := TimedCallSystem('pwd')[2];
if SearchDelim('/',pwd[1..-2])[-1]<>'BenchmarkService' then
printf('wrong working directory. Should be at BenchmarkService'); quit; fi:

ReadProgram('lib/darwinit');
ddir := eval(symbol(lowercase('$dataset').'DBpath'));
IDDB := LoadIndex(ddir.'IDIndex.db');

EC := CreateArray( 1..NrOfProteins('$dataset') ):
c_inOma := Counter('number of proteins mappable to OMA');
c_all   := Counter('total Proteins with EC numbers');

ReadProgram('$enzDrw');
for ECclass in ec do 
#   ecs := append(ecs, ECclass[1]);
    for id in ECclass[3] do
        c_all + 1;
        oE := SearchIndex(id, IDDB);
        if oE<>NULL then 
            c_inOma + 1;
            if EC[oE]=0 then EC[oE] := {ECclass[1]};
            else EC[oE] := append(EC[oE], ECclass[1]);
    	    fi:
        fi:
    od: 
od:
OpenWriting('$enzDat');
printf('# %s: %d ; in OMA: %d (%.1f%%)\n', c_all['title'], 
    c_all['value'], c_inOma['value'], c_inOma['value']/c_all['value']*100);
printf('EC := %A:\n', EC);
OpenWriting(previous);
done
EOA

gzip -v9 $enzDat
rm -f $enzRaw $enzDrw
