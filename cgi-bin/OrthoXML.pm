package OrthoXML;
use base qw(XML::SAX::Base);

my( $relFh, $cSpec, $prot_idMap, $inGenes, $inCluster, @cluster, $cnts );
sub new {
    my $type = shift;
    $relFh = shift;
    $cSpec=0; $prot_idMap={}; $inGenes=0; $cnts=0;
    return bless {}, $type;
}

sub get_nr_of_relations{
    return( $cnts );
}

sub start_element{
    my ($self, $element) = @_;
   
    #print $element->{Name}."\n";
    if ($element->{Name} eq "species") {
        $cSpec++;
    }
    elsif ($element->{Name} eq "genes") {
        $inGenes++;
    } 
    elsif ($element->{Name} eq "gene"){
        if ($inGenes){ 
            my $pid = $element->{Attributes}->{"{}protId"}->{Value};
            my $id = $element->{Attributes}->{"{}id"}->{Value};
            $prot_idMap->{$id} = $pid;
        }
    }
    elsif ($element->{Name} eq "cluster"){
        $inCluster++;
    }
    elsif ($element->{Name} eq "geneRef"){
        if ($inCluster) {
            push( @cluster, $element->{Attributes}->{"{}id"}->{Value} );
	}
    }
    elsif ($element->{Name} eq "clusters"){
        @cluster = ();
    }
}

sub end_element{
    my ($self, $element) = @_;

    if ($element->{Name} eq "cluster"){
        print $relFh "GroupRelations := ([\n";
        for my $k (@cluster){
	    print $relFh " '".$prot_idMap->{$k}."',\n";
	}
	print $relFh " NULL]):\n";
	my $c = scalar @cluster;
	$cnts += ($c*($c-1)/2);
	@cluster = ();
	$inCluster--;
    }
}

1;
