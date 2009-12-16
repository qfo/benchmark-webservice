package SeqXML;
use base qw(XML::SAX::Base);

my( $writer, $curSpecName, @specs );


sub new {
    my $type = shift;
    $writer = shift;
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
	print $writer 
    }
    
}

sub characters {

}

sub end_element {

}
