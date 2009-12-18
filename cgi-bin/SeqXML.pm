package SeqXML;
use base qw(XML::SAX::Base);

my( $seqFh, $spsFh, $curSpecName, @specs, $cnts );

sub new {
    my $type = shift;
    $seqFh = shift;
    $spsFh = shift;
    $cnts=0;
    return bless {}, $type;
}

sub get_nr_of_sequences{
    return( $cnts );
}

sub start_element {
    my ($self, $element) = @_;
#    print $element->{Name}."\n";

    if ($element->{Name} eq "species") {
	$curSpecName = $element->{Attributes}->{"{}longname"}->{Value};
	push( @specs, $curSpecName );
    }
    elsif ($element->{Name} eq "protein") {
        my $attr = $element->{Attributes};
#        for my $k (keys(%$attr)) { 
#	  for my $i (keys(%{$attr->{$k}})) {
#	  print "$k -> $i ->".$attr->{$k}->{$i}."\n"; }}
	
	my $id  = $attr->{"{}prot_id"}->{Value};
	my $seq = $attr->{"{}seq"}->{Value};
	$seq =~ s/[^ACDEFGHIKLMNPQRSTVWXY]/X/g;
        print $seqFh "Protein := ['$id','$curSpecName','$seq']:\n";
	$cnts++;
    }
}

sub end_document {
    print $spsFh "SPS := [\n";
    for my $k (@specs) { print $spsFh "'$k',\n"; }
    print $spsFh "NULL]:\n";
}

1;
