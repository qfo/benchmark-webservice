#!/usr/bin/perl -w
use strict;

# extract BRH pairs between each pair of genomes
# cecile pereira
# 10 janv 2016
# perl 2_BRH.pl [output directory] [Best hit directory]

# Parameters
my $dirWork = $ARGV[0]; # output directory

# Best hit (one direction)
my $dirInBH = $ARGV[1]; #INPUT : Besthit one direction directory
my $dirOutBRH = $dirWork.'BRH/'; #Output : directory


# Variables
my $geno1 = 0; #first specie
my $geno2 = 0; #genome BD
my $file = '';
my @TmpGeno = (); #genome names
my @AllGeno = (); #genome names
my @File = ();
my %lgenomes=(); #genome names
my $BHfile="";#
my $lgenomes="";
my @tmp=();

###########
#Program
###########

# create OUTPUT
mkdir($dirOutBRH) unless (-e $dirOutBRH);

# genome list
chdir($dirInBH);
@TmpGeno = glob("*.tab"); 
foreach $BHfile (@TmpGeno) {
	$BHfile=~s/^BH_//;
	$BHfile=~s/\.tab$//;
	@tmp=split("_",$BHfile);
	$lgenomes{$tmp[0]}="";
	$lgenomes{$tmp[1]}=""
}


# order by alphabetical order
@AllGeno = sort(keys(%lgenomes));

#extract BRH by pair
for ($geno1 = 0; $geno1 < $#AllGeno; $geno1 ++) {
	for ($geno2 = $geno1+1; $geno2 <= $#AllGeno; $geno2++) {
		unless(-e $dirOutBRH."BRH_$AllGeno[$geno1]\_$AllGeno[$geno2].txt"){
			# if one of the both genomes is new we extract the BRH for the pair
			print "Extract BRH between $AllGeno[$geno1] and $AllGeno[$geno2]\n";
	 		BHR($dirWork, $AllGeno[$geno1], $AllGeno[$geno2],$dirInBH,$dirOutBRH); 
	 	}
  }
}

###########
#Fonction
###########
#extract BRH for a pair of genomes
sub BHR {
	my ($dirWork, $esp1, $esp2, $dirIn,$dirOut) = @_;
	my @Line = (); 
	my @File = ();
	my %Genome2 = (); 
	my $file = '';

	chdir($dirIn);
	@File = glob("BH_$esp2\_$esp1.tab");
	if ($#File >= 0){
		foreach $file (@File) {
			#lecture des resultats
			open BH21,$dirIn.$file ;
			while (<BH21>) {
				chomp;
				@Line = split ("\t",$_); #[0] id query, [1] BH
				$Genome2{$Line[0]}{$Line[1]} ="" ;
			}
			close (BH21);
		}
	}
	else{
		die ("No BH files for $esp2 and $esp1\n");
		print "No BH files for $esp2 and $esp1\n";
	}
	#Studie of the reciprocal blast
	#result file
	open BHR, '>'.$dirOutBRH."BRH_$esp1\_$esp2.txt";
	@File = glob("BH_$esp1\_$esp2.tab");
	if ($#File >= 0){
		foreach $file (@File) {
			open BH12,$dirIn.$file;
			while (<BH12>) {
				chomp;
				@Line = split ("\t",$_); #[0] id query, [1] BH
				#if best hit in the both comparisons A vs B and B vs A
				if (exists($Genome2{$Line[1]}{$Line[0]})) {
					 print BHR "$Line[0]\t$Line[1]\n";
				}
			}
			close(BH12);
		}
	}
	else{
		die ("No BH files for $esp1 and $esp2\n");
		print "die because No BH files for $esp1 and $esp2\n";
	}
	close(BHR);
}

