#!/usr/bin/perl
use strict; 
use warnings;

# take a enzyme classification  input file and generate a darwin
# datastructure with the IDs that is printed to STDOUT

# state s -> starting
# state n -> new family
# state n1-> header done
# state a -> appending
# state e -> ended appending

my $state = "s"; 
my $l = 0;
open(IN,"<$ARGV[0]");
open(OUT,">$ARGV[1]");
print OUT "ec := [];";
while (<IN>) {
    s/'/"/g;
    $l++;
    if (/^ID +([\d\.]*)/) {
        #if ($state eq "n") {
        #    die "empty family on line $l (state $state)\n";
        #}
        if ($state ne 's'){
            print OUT "NULL}]):\n";
        }
        print OUT "ec := append(ec,['$1',";
        $state = "n";
    }
    elsif (/^DE +(.*)/) {
        if ($state ne "n" and $state ne "n1") {
            die "have a description without an EC number on line $l\n";
        }
        elsif ($state ne "n1") {
             print OUT "'$1',{\n";
             $state = 'n1'
        }
    }
    elsif (/^DR/) {
        die unless ($state eq "a" or $state eq "n1" or $state eq "n");
        my @chunks = split(/; /);
        foreach my $i (@chunks) {
            if ($i =~/(\w{6}),\s*(\w{1,5})_(\w{3,5})/) {
                $state = "a";
                my $org = $3;
                if ($org eq "RAT") { $org="RATNO"; }
                elsif ($org eq "PIG") { $org="PIGXX"; }
                
                print OUT "'$1','$2_$org',";
            } else {
	        print $i;
	    }
        }
    }
    if ($state eq 'a' and /^\/\//) {
        $state = 'e';
    }
}
print OUT "NULL}]);"; 
close(IN); close(OUT);
