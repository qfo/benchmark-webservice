#!/bin/bash

name="reference17"
root="/pub/scratch/adriaal/refgenomes"

darwin -E << EOF
 wdir := '$root';
 ReadProgram('GenerateSpeciesInfo.drw');
 done;
EOF

#inputs=$(find -H $root/raw -name "*.seqxml.gz")
python Converter.py --speciesinfo=$root/SpeciesInfo.txt --datadir=$root/genomes $root/raw/*/*.seqxml.gz 

export DARWIN_GENOMES_PATH=$root/genomes
export DARWIN_OMADATA_PATH=/pub/projects/cbrg-ortholog-benchmark-service/$name

echo "genomes := []:" > $DARWIN_GENOMES_PATH/Summaries.drw
echo "GenomeSummaries := table():" >> $DARWIN_GENOMES_PATH/Summaries.drw
echo "GenomeFileName := table():" >> $DARWIN_GENOMES_PATH/GenomeFileName.drw

for db in $(find $DARWIN_GENOMES_PATH -mindepth 1 -type d -printf "%f\n"); do
    dbfn=$(ls $DARWIN_GENOMES_PATH/$db/$db*.db);
    echo "GenomeFileName['$db'] := '$dbfn';" >> $DARWIN_GENOMES_PATH/GenomeFileName.drw

    darwin << EOF
       ReadProgram('$DARWIN_OMA_REPO_PATH/lib/darwinit');
       AddSummary('$db');
       done
EOF
done

mkdir -p $DARWIN_OMADATA_PATH
darwin -E << EOF
    ReadProgram('GenerateIDMapAndSeqDb.drw');
    done;
EOF
cp $DARWIN_GENOMES_PATH/Summaries.drw $DARWIN_OMADATA_PATH
gzip -f9 $DARWIN_OMADATA_PATH/Summaries.drw

