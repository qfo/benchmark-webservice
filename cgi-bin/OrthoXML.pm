package OrthoXML;
use base qw(XML::SAX::Base);

sub start_element{
    my ($self, $element) = @_;
    
    if ($element->{Name} eq 'species') {\
       
    } 
    elsif (){
    }
    
}

sub characters {

}

sub end_element{

}

