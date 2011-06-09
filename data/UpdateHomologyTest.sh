#!/bin/bash

# default values
DATASET="RefSet5"

while getopts "d:" opt ; do
    case $opt in
    d) DATASET="$OPTARG";;
    h|?) 
      echo "options are -d DATASET"
      exit 0;;
    *) 
      echo "invalid option"
      exit 1;;
    esac
done

DATA=$(dirname $0)
RAW=$DATA/raw
DARWIN="/local/bin/darwin64"

OUTFILE="$DATA/homologyTest_$DATASET.drw"

$DARWIN -B << EOA
ReadProgram('lib/darwinit');
ddir := eval(symbol(lowercase('$DATASET').'DBpath'));
IDIndex := ReadDb(ddir.'IDIndex.db');
SeqDB := ReadDb(ddir.'ServerSeqs.db');

MapSequence := proc(s, rans, db:database)
    global DB:
    curDB := DB:
    DB := db:
    nRan := length(rans):
    ssd := SearchSeqDb(s);
    if ssd[1,2] > ssd[1,1] then eNr := NULL; 
    else
        es := [seq(GetEntryNumber(e),e=[Entry(ssd)])];
        en := [];
        for eNr in es do 
            for i to nRan while eNr>=rans[i,2] do od:
            if i<=nRan and rans[i,1]<=eNr and rans[i,2]>=eNr then 
                en := append(en,eNr);
            fi
        od:
        if length(en)=1 then eNr := en[1]; else eNr := NULL fi:
    fi:
    DB := curDB:

    return(eNr);
end:


MapProteins := proc(seqs:list, ids:list)
    c  := Stat('mapped sequences');
    cS := Counter('only sequence mapped');
    cI := Counter('only id mapped');
    cD := Counter('id and sequence do not map to same eNr');
    rans := {seq( GenomeRange(z,'$DATASET'), z=[HUMAN,MOUSE])};
    mapping := []:
    for i to length(ids) do
        idMap := SearchIndex(ids[i], IDIndex):
        seqMap := MapSequence(seqs[i], rans, SeqDB);
        
        if idMap=NULL and seqMap=NULL then c+0; next;
        else
            c + 1;
            if idMap=NULL then cS + 1; eNr := seqMap;
            elif seqMap=NULL then cI + 1; eNr := idMap;
            elif idMap<>seqMap then cD + 1; next;
            elif idMap=seqMap then eNr := idMap;
            fi:
        fi:
        mapping := append(mapping, [ids[i], eNr]):
    od:
    print(c,cS,cI,cD);
    return( mapping );
end:

MapId2ENr := proc(id, map)
    i := SearchOrderedArray(id, map[1]);
    if i<=0 or i>length(map[1]) or map[1,i]<>id then NULL;
    else map[2,i] fi:
end:

MapPairsFromFile := proc(fn:string, map)
    OpenPipe('zcat '.fn):
    pairs := []:
    err := Counter('# of ignored pairs due to error');
    c_m := Counter('# of mapped pairs');
    line := ReadRawLine();
    while line<>EOF do
        rawPair := SearchDelim('\t',line[1..-2]);
        line := ReadRawLine();
        if length(rawPair)<>2 then err+1; next fi:

        eNrs := {seq(MapId2ENr(z, map), z=rawPair)};
        if length(eNrs)=2 then pairs := append(pairs, eNrs); c_m+1 fi:
    od:
    print(err, c_m);
    return(pairs);
end:

ExcludeSameSpeciesPairs := proc(pairs:list)
    filtered := []:
    for pair in pairs do 
        s := {seq(GenomeNrFromENr(z,'$DATASET'), z=pair)};
        if length(s)=2 then filtered := append(filtered, pair) fi:
    od:
    return( filtered );
end:

Reformat := proc(pairs_:list)
    nP := NrOfProteins('$DATASET');
    data := CreateArray(1..nP,{}):
    pairs := sort(pairs_):
    cur := pairs[1,1]; partners := [pairs[1,2]]:
    for pair in pairs do 
        if pair[1]<>cur then
            data[cur] := {op(partners)};
            cur := pair[1]; partners := [];
        fi;
        partners := append(partners, pair[2]);
    od:
    data[cur] := {op(partners)};
    return( data );
end:

        
fasta := ReadFastaWithNames('$RAW/homologyTest.fasta'):
map2oENr := transpose(sort(MapProteins( op(fasta) ))):
posAll := MapPairsFromFile( '$RAW/homologyTest.pos.dat', map2oENr ):
negAll := MapPairsFromFile( '$RAW/homologyTest.neg.dat', map2oENr ):

pos := Reformat( ExcludeSameSpeciesPairs(posAll) ):
neg := Reformat( ExcludeSameSpeciesPairs(negAll) ):

nP  := NrOfProteins('$DATASET');


Set(quiet);
OpenWriting('$OUTFILE');
printf('# $DATASET dataset, created %s\n', date());
printf('pos := table(): neg := table():\n');
printf('__TMP := CreateArray(1..%d,{}):\n',nP);
for i to nP do if length(pos[i])>0 then
    printf('__TMP[%d] := %A:\n', i, pos[i]);
fi od:
printf('pos[''HumMus''] := __TMP:\n);
printf('__TMP := CreateArray(1..%d,{}):\n',nP);
for i to nP do if length(neg[i])>0 then
    printf('__TMP[%d] := %A:\n', i, neg[i]);
fi od:
printf('neg[''HumMus''] := __TMP:\n'):
OpenWriting(previous);
EOA

gzip -v9 $OUTFILE
exit 0;
