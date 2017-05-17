#!/bin/bash
dataset="${1:-RefSet5}"
enzRaw="/tmp/enzymes.dat"
enzDrw="/tmp/enzymes.drw"
enzDat="$DARWIN_ORTHOLOG_BENCHMARKDATA_PATH/data/enzymes_$dataset.drw"
gen_dir="$(dirname $0)"

wget "ftp://ftp.expasy.org/databases/enzyme/enzyme.dat" -O $enzRaw
if [ $? -ne 0 ] ; then echo "could not download enzyme.dat"; exit 1; fi

$gen_dir/convert_ec.pl $enzRaw $enzDrw
if [ $? -ne 0 ] ; then echo "could not convert enzymes into darwin format"; exit 1; fi


darwin  << EOA
wdir := getenv('DARWIN_ORTHOLOG_BENCHMARK_REPO_PATH');
if wdir='' then error('DARWIN_ORTHOLOG_BENCHMARK_REPO_PATH not set') fi:
ReadProgram(wdir.'/lib/darwinit');
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
