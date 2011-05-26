package OrthoXML;
use base qw(XML::SAX::Base);

my( $relFh, $cSpec, $prot_idMap, $inGenes, $inOG, $inPG, $curGroup, $cnts );
sub new {
    my $type = shift;
    $relFh = shift;
    $cSpec=0; $prot_idMap={}; $inGenes=0; $cnts=0; $inOG=0; $inPG=0;
    return bless {}, $type;
}

sub get_nr_of_relations{
    return( $cnts );
}

sub start_element{
    my ($self, $element) = @_;
   
    print $element->{Name}."\n";
    if ($element->{Name} eq "species") {
        $cSpec++;
    }
    elsif ($element->{Name} eq "genes") {
        $inGenes++;
    } 
    elsif ($element->{Name} eq "gene"){
        ($inGenes > 0) or die("gene definition outside genes tag");
        my $pid = $element->{Attributes}->{"{}protId"}->{Value};
        my $id = $element->{Attributes}->{"{}id"}->{Value};
        $prot_idMap->{$id} = $pid;
    }
    elsif ($element->{Name} eq "orthologGroup"){
        $inOG++;
        $curGroup .= "OG(";
    }
    elsif ($element->{Name} eq "paralogGroup"){
        $inPG++;
        $curGroup .= "PG(";
    }
    elsif ($element->{Name} eq "geneRef"){
        ($inOG>0) or die("geneRef tag outside orthologGroup tag");
        my $geneid = $element->{Attributes}->{"{}id"}->{Value};
        $curGroup .= "'".$prot_idMap->{$geneid}."',";
    }
    elsif ($element->{Name} eq "groups"){
        $curGroup = "";
    }
}

sub end_element{
    my ($self, $element) = @_;
    if ($element->{Name} eq "genes"){
        (--$inGenes == 0) or  die("unexpected closing 'genes' tag");
    } elsif ($element->{Name} eq "orthologGroup"){
        $curGroup .= "NULL)";
	$inOG--;
        if ($inOG==0){
            print $relFh "$curGroup:";
            $curGroup = "";
            $cnts += 1;
        }
    } elsif ($element->{Name} eq "paralogGroup"){
        $curGroup .= "NULL)";
        $inPG--;
        $inOG>0 or die("not nested 'paralogGroup' tag");
    }
}

1;
