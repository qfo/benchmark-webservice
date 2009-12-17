package OrthoXML;
use base qw(XML::SAX::Base);

my( $cSpec, %prot_idMap, $inGenes);
sub new {

}

sub start_element{
    my ($self, $element) = @_;
    
    if ($element->{Name} eq "species") {
        cSpec++;
    }
    elsif ($element->{Name} eq "genes") {
        $inGenes++;
    } 
    elsif ($elements->{Name} eq "gene"){
        if ($inGenes){ 
            my $pid = $element->{Attributes}->{"protId"};
            my $id = $element->{Attributes}->{"geneId"};
            %prot_idMap{$id} = $pid;
        }
    }
    
}

sub characters {

}

sub end_element{

}

