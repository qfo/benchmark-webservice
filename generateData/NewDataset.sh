#!/bin/bash

name="RefSet17"
root="/pub/scratch/adriaal/refgenomes"

cat > darwin << EOF
 wdir := '$root';
 ReadProgram('GenerateSpeciesInfo.drw');
 done;
EOF

inputs=$(find $root/raw -name "*.seqxml.gz")
python Converter.py --speciesinfo=$root/SpeciesInfo.txt --datadir=$root/genomes < $inputs



