#!/usr/bin/perl
#
#  convertion of orthoMCL (last checked version 3) data
#

use strict;
use warnings;

my $tit = "'OrthoMCL v3'";
my $fnBase = "/local/BenchmarkService/projects/pub_OrthoMCL.".int(1000*rand());
my $nrProt = 0;
my $nrGrps = 0;
print $fnBase ."\n";

my %grps=(); 
my %sps=();

open( IN, "zcat <$ARGV[0] |");
open( SEQ, ">$fnBase.seqs");
while( <IN> ){
    chomp;
    if (/^>([\w\|_\.-]+)\s\|\s((OG\d+_\d+)|(no_group))\s\|\s(.*)$/) {
        my $id  = $1;
	my $grp = $2;
	my $rest = $5;
	my $org;
	if ($rest =~ /\[\s?(\w+ [\w\. -]+)\s?\]\s?$/) { $org = $1;} 
	else { my @t=split( /\|/, $id); $org = $t[0]; }
#print "$id\n$grp\n$rest\n$org\n\n";

	$sps{$org}=1;
	if ($grp ne "no_group") {
	    @{$grps{$grp}} = () if not defined($grps{$grp});
	    push(@{$grps{$grp}}, $id);
	}
        print SEQ "']:\n" if ($nrProt>0);
	print SEQ "Protein := ['$id','$org','";
	$nrProt++;
    }
    else {
        uc;
	s/\*$//;
	s/[^ACDEFGHIKLMNPQRSTVWXY]/X/g;
	print SEQ;
    }
}
print SEQ "']:\n";
close( SEQ );

# write the group file
open( GRP, ">$fnBase.rels" );
for my $k (keys(%grps)){
    $nrGrps++;
    my $rowl=0;
    print GRP "GroupRelations( # $k\n[";
    foreach my $x (@{$grps{$k}}) { 
        print GRP "'$x',";
	print GRP "\n" if ((++$rowl % 10)==0);
    }
    print GRP "NULL]):\n";
}
close( GRP );

# write the sps file
open( SPS, ">$fnBase.sps" );
print SPS "SPS := [\n";
for my $k (keys( %sps )){ print SPS "'$k',\n";}
print SPS "NULL]:\n";
close( SPS );
        
system("perl gateway.pl UploadData \\'$fnBase\\' \\'$tit\\' $nrProt $nrGrps");
