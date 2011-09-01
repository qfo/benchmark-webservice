package OrthoXML;
use base qw(XML::SAX::Base);

my( $relFh, $cSpec, $prot_idMap, $inGenes, $inOG, $inPG, $curGroup, $cnts, $lastAlive );
sub new {
    my $type = shift;
    $relFh = shift;
    $cSpec=0; $prot_idMap={}; $inGenes=0; $cnts=0; $inOG=0; $inPG=0;
    $lastAlive=time();
    return bless {}, $type;
}

sub get_nr_of_relations{
    return( $cnts );
}

sub start_element{
    my ($self, $element) = @_;
   
    if ($element->{Name} eq "orthoXML") {
        my $orthoxmlVersion = $element->{Attributes}->{"{}version"}->{Value};
        die("requires orthoxml version 0.3") unless ($orthoxmlVersion eq "0.3");
    }
    elsif ($element->{Name} eq "species") {
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
        $curGroup .= "OG(";
        $inOG++;
    }
    elsif ($element->{Name} eq "paralogGroup"){
        $inPG++;
        $curGroup .= "PG(";
    }
    elsif ($element->{Name} eq "geneRef"){
        ($inOG>0) or die("geneRef tag outside orthologGroup tag:".$element->{Attributes}->{"{}id"}->{Value});
        my $geneid = $element->{Attributes}->{"{}id"}->{Value};
        $curGroup .= "'".$prot_idMap->{$geneid}."',";
    }
    elsif ($element->{Name} eq "groups"){
        $curGroup = "";
    }
#    if (time() - $lastAlive > 15 ){
#        if ($inGenes>0) {print "in genes\n";}
#        elsif ($inOG>0) {print "in OG\n";}
#        else {print "don't know\n";};
#        $lastAlive = time();
#    }
}

sub end_element{
    my ($self, $element) = @_;
    if ($element->{Name} eq "genes"){
        (--$inGenes == 0) or  die("unexpected closing 'genes' tag");
    } elsif ($element->{Name} eq "orthologGroup"){
        $curGroup .= "NULL)";
	$inOG--;
        if ($inOG==0){
            print $relFh "GroupRelations( $curGroup ):\n";
            $curGroup = "";
            $cnts += 1;
        }
        else{
            $curGroup .= ",";
        }
    } elsif ($element->{Name} eq "paralogGroup"){
        $curGroup .= "NULL),";
        $inPG--;
        $inOG>0 or die("not nested 'paralogGroup' tag");
    }
}

1;
