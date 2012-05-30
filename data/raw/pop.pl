#!/sw/bin/perl5.8.8
use SOAP::Lite;# +trace => [debug];
use Data::Dumper;

my %map = (
'POP1_HUMAN' => 'ENSG00000112276',
'POP1_MACMU' => 'ENSMMUG00000014471',
'POP1_MOUSE' => 'ENSMUSG00000071317',
'POP1_RAT' => 'Q3BCU4',
'POP1_RABIT' => 'ENSOCUG00000016944',
'POP1_MONDO' => 'ENSMODG00000018034',
'POP1_ORNAN' => 'ENSOANG00000004180',
'POP1_CHICK' => 'ENSGALG00000015410',
'POP1_TAEGU' => 'ENSTGUG00000012218',
'POP1_ANOCA' => 'ENSACAG00000003910',
'POP1_XENTR' => 'ENSXETG00000013301',
'POP1_DANRE' => 'ENSDARG00000058548',
'POP1_ORYLA' => 'ENSORLG00000019663',
'POP1_GASAC' => 'ENSGACG00000014015',
'POP1_TAKRU' => 'ENSTRUG00000008719',
'POP1_CIOIN' => 'ENSCING00000000496',
'POP1_CIOSA' => 'ENSCSAVG00000000247',
'POP2_HUMAN' => 'ENSG00000121577',
'POP2_MACMU' => 'ENSMMUG00000000905',
'POP2_MOUSE' => 'ENSMUSG00000022803',
'POP2_RAT' => 'ENSRNOG00000002994',
'POP2_RABIT' => 'ENSOCUP00000008208',
'POP2_MONDO' => 'ENSMODG00000018205',
'POP2_MACEU' => 'ENSMEUG00000015825',
'POP2_CHICK' => 'ENSGALG00000014988',
'POP2_TAEGU' => 'ENSTGUG00000013383',
'POP2_ANOCA' => 'ENSACAG00000003557',
'POP2_XENTR' => 'ENSXETG00000018064',
'POP2_DANRE' => 'ENSDARG00000069922',
'POP2_ORYLA' => 'ENSORLG00000008627',
'POP2_GASAC' => 'ENSGACG00000001420',
'POP2_TAKRU' => 'ENSTRUG00000015933',
'POP3_HUMAN' => 'ENSG00000132429',
'POP3_MACMU' => 'ENSMMUG00000014473',
'POP3_MOUSE' => 'ENSMUSG00000019848',
'POP3_RAT' => 'Q3BCU3',
'POP3_RABIT' => 'ENSOCUG00000025973',
'POP3_MONDO' => 'ENSMODG00000018033',
'POP3_ORNAN' => 'ENSOANG00000004179',
'POP3_CHICK' => 'ENSGALG00000015410',
'POP3_XENTR' => 'ENSXETG00000024466',
'POP3_DANRE' => 'ENSDARG00000058551',
'POP3_ORYLA' => 'ENSORLG00000019669',
'POP3_GASAC' => 'ENSGACG00000014023',
'POP23a_BRAFL' => 'C3ZMF1',
#'POP23b_BRAFL' => '121417',
'POP23b_CIOIN' => 'ENSCING00000016169',
'POP23a_CIOIN' => 'ENSCING00000016202',
'POP23_CIOSA' => 'ENSCSAVG00000000248'
);

my $service = SOAP::Lite -> uri('urn:/OMA')
             -> proxy('http://omabrowser.org/cgi-bin/soap.pl');

#my $result = $service->Reload(); 
my @keys = values %map;
my @keys2 = keys %map;
my $result = $service->MapIDs(\@keys,0); 
my $res = $result->valueof('//MapIDsResponse/OutIDss');

foreach my $i (0..$#keys) {
    print "[$keys2[$i], @{$res->[$i]}],\n";
}
print "\n\n";

####