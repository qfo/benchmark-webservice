#!/usr/bin/perl -w
use strict;
# extract Best Hit between pairs of genomes
# last modification the 10 jan 2016 by Cecile Pereira
# - best hits (several) E-value cutoff of 0.01 and consider >=99% of the highest score a BBH hit. This was how Wolf and Koonin (Genome Biol Evol 2012) did it.

#perl 1_BRH_job.pl [blastp file] [output repertory] [name of the output file]

#############
#Declaration
#############

# Arguments 
my $fileInBlast = $ARGV[0]; # INPUT : nom du fichier resultat genere par le programme BLAST
my $dirOutBH = $ARGV[1]; # OUTPUT : repertoire final contenant tous les fichiers complets
my $fileOutBH = $ARGV[2]; # OUTPUT : nom du fichier a generer

# Autres variables
my $id = '';
my @Line = ();
my $BestScore=0;
my $scoretmp=0;
my $continu=0;
my $cutoffeval=0.01;#cutoff evalue
my $pcscore=0.99;#at least 99% score first hit => best hit

############
#Programme
#############

# if input file exist
die ("Error : No Output file $fileInBlast (1_BRH_job.pl)\n") unless (-e $fileInBlast);

# read blastp
open IN,$fileInBlast;
# write best hit
open OUT,'>'.$dirOutBH.$fileOutBH;
while (<IN>) {
	unless(/^#/){
	    chomp($_);
	    @Line = split(/\t/,$_);
	    if($Line[10]<=$cutoffeval){#cutoff evalue
		$continu=1;#best hit or not?
		if($id eq $Line[0]) {# id query already seen
			$scoretmp=$Line[11];
			if($scoretmp>=($BestScore*$pcscore)){# test the length of the alignment
			    $continu=1;
			}
			else{
			    $continu=0;
			}
		}
		if($continu==1){
			#query, subject
			print OUT "$Line[0]\t$Line[1]\n" ;
			$id = $Line[0]; # ID query blastp
			$BestScore=$Line[11];
		}
	    }
	}
}
close(IN);
close(OUT);
