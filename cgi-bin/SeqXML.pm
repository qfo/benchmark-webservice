package SeqXML;
use base qw(XML::SAX::Base);

my( $seqFh, $spsFh, $curSpecName, @specs );


sub new {
    my $type = shift;
    $seqFh = shift;
    $spsFh = shift;
    return bless {}, $type;
}

sub start_element {
    my ($self, $element) = @_;
    
    if ($element->{Name} eq "species") {
        my %attr = $element->{Attributes};
	$curSpecName = $attr->{"longname"};
	push( @specs, $curSpecName );
    }
    elsif ($element->{Name} eq "protein") {
        my %attr = $element->{Attributes};
	    my $id  = $attr->{"prot-id"};
	    my $seq = $attr->{"seq"};
        print $seqFh "Protein := ['$id','$curSpecName','$seq']:\n";
    }
}

sub end_document {
    print $spsFh "SPS := [\n";
    for my $k (@specs) { print $spsFh "'$k',\n"; }
    print $spsFh "NULL]:\n";
}
