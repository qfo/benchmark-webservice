#!/bin/bash 

root=/pub/scratch/adriaal/bbh
blast_root=$root/blastp
res_root=$root/res/

for f in $blast_root/; do 
    perl 1_BRH.pl $res_root $blast_root
    perl 2_RBH.pl $res_root $res_root/BH
done

cat $res_root/BRH/*txt > $res_root/bbh.txt

