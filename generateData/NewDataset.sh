#!/bin/bash

########################################################################
# Creates a new version for a reference proteome dataset from QfO      #
# - Set name to the name of the resulting folder in the project share  #
# - set root to a folder that will contain the temporary data and a    #
#   symlink 'raw' pointing to the extracted seqxml files.              #
########################################################################

name="reference22"
root="/work/FAC/FBM/DBC/cdessim2/default/aaltenho/obs22/"

export DARWIN_OMA_REPO_PATH=${HOME}/OMA
export DARWIN_GENOMES_PATH=$root/genomes
export DARWIN_OMADATA_PATH=/work/FAC/FBM/DBC/cdessim2/default/aaltenho/$name
export DARWIN_ORTHOLOG_BENCHMARK_REPO_PATH="$(cd $(dirname $0)/../ && pwd)"
mkdir -p $DARWIN_GENOMES_PATH

darwin -E << EOF
 wdir := '$root';
 ReadProgram('GenerateSpeciesInfo.drw');
 done;
EOF

#inputs=$(find -H $root/raw -name "*.seqxml.gz")
python Converter.py --speciesinfo=$root/SpeciesInfo.txt --datadir=$root/genomes $root/raw/*/*[0-9].xml 

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

darwin -E -q << EOF
    ReadProgram('$DARWIN_GENOMES_PATH/Summaries.drw');
    GS := GenomeSummaries:
    OpenWriting('$DARWIN_GENOMES_PATH/species.txt');
    for g in genomes do
	printf('%s\t%s\n', g, GS[g, 'TAXONID']);
    od:
    done
EOF

mkdir -p $DARWIN_OMADATA_PATH
darwin -E << EOF
    ReadProgram('GenerateIDMapAndSeqDb.drw');
    done;
EOF
cp $DARWIN_GENOMES_PATH/Summaries.drw $DARWIN_OMADATA_PATH
gzip -f9 $DARWIN_OMADATA_PATH/Summaries.drw

grep -h '>sp|' $root/raw/{Eukaryota,Archaea,Bacteria}/*[0-9].fasta | sed -e "s/\s.*$//" | gzip > $DARWIN_OMADATA_PATH/swissprot.txt.gz

