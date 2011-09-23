#!/usr/bin/perl

use XML::SAX;
use XML::Validator::Schema;
use OrthoXML;
use strict;




sub SeqXML2Drw {
    my ($fh, $fnSeq, $fnSps) = @_;
    
    my ($seqFh, $spsFh);
    open( $seqFh, ">$fnSeq");
    open( $spsFh, ">$fnSps");
    my $handler = SeqXML->new($seqFh, $spsFh);
    my $parser = XML::Parser::Lite->new(Handler => $handler);
    $parser->parse($fh);
    close( $seqFh );
    close( $spsFh );
    return( $handler->get_nr_of_sequences());

}

sub RelXML2Drw {
    my ($fh, $fn) = @_;
    
    my $relFh;
    open( $relFh, ">$fn");
    print "outfile opened\n";
    my $handler = OrthoXML->new($relFh);
    print "handler created\n";
    
#    my $validator = XML::Validator::Schema->new(file => 'orthoxml.xsd');

    # create a SAX parser and assign the validator as a Handler
    #
#    my $parser = XML::SAX::ParserFactory->parser(Handler => $validator);

    #
    # validate foo.xml against foo.xsd
    #
#    eval { $parser->parse_file($fh) };
#      die "File failed validation: $@" if $@;

    my $parser = XML::SAX::ParserFactory->parser(Handler => $handler);
    print "parser created\n";
    $parser->parse_file($fh);
    print "finished parsing\n";
    close( $relFh );
    return( $handler->get_nr_of_relations());
}

#sub RelText2Drw {
#    my ($fh, $fn) = @_;
#    
#    my $cnt = 0;
#    open(F,">$fn") or die($!);
#    open( RAW, ">$fn.raw") or die($!) if $storeRaw; 
#    print F "PairRelations([\n";
#    while( <$fh> ){
#        print RAW $_ if $storeRaw;
#        chomp;
#    if ( /([\w.-]*)\t([\w.-]*)/ ){
#       print F "['$1','$2'],\n";
#       $cnt++;
#       if ($cnt % 50000 == 0){ print F "NULL]):\nPairRelations([\n";}
#        }
#    }
#    print F "NULL]):\n";
#    close(F);
#    close(RAW) if $storeRaw;
#    return($cnt);
#}

my $FH ;#= $ARGV[0];
open( $FH, "<$ARGV[0]") or die($!);
#while (<$FH>) {
#    print $_;
#}
#close($FH);
my $cnt = RelXML2Drw( $FH, $ARGV[1] );
close($FH);
