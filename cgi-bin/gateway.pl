#!/usr/bin/perl

use CGI qw/:standard delete_all/;
use CGI::Cookie;
use POSIX qw/mkfifo strftime/;
use CGI::Carp qw/carpout fatalsToBrowser set_message/;
use File::stat;
use File::Basename;
use Time::localtime;
use IO::Zlib;
use IO::Uncompress::Bunzip2 qw(bunzip2 $Bunzip2Error) ;
use IO::Uncompress::Gunzip qw(gunzip $GunzipError) ;
use IO::File;

use XML::SAX;
use SeqXML;
use OrthoXML;
use strict;



# To Do:
#   - when "under maintenance", block all requests for at least 20 seconds
#
# vars: f, p1 to pn
#  ex: 
#    f=DisplayEntry&p1=1523 -> omaDisplayEntry(1523)
#    f=SearchDb&p1=AATCGCTAAA -> omaSearchDb('AATCGCTAA')
srand (time ^ $$ ^ unpack "%L*", `ps axww | gzip`);
my $cook = '';
my $debug = 0;
my $storeRaw = 1;
my $error_log = '/local/BenchmarkService/output';
my $dbg_log = '/local/BenchmarkService/dbg.log';
my $upload_log = '/local/BenchmarkService/upload.log';

BEGIN {
    unshift @INC, '/local/BenchmarkService/lib';
}
# maximum Post size in bytes 
$CGI::POST_MAX = 1<<32;
$|++; # disable buffering of stdout

#use Time::HiRes qw(time);
my $hostname = `/bin/hostname`;
chomp($hostname);
my $din = 'BSin.'.$hostname;
my $pDarwin = '/tmp/'.$din;


# in debug mode, open the dbg log file for appending...
open(DBGLOG, ">>$dbg_log") if $debug;
print "Content-type: text/html\n\n" if $debug;

# we first parse the request
my $req = new CGI;

# construct cookies table:
my %cookies = fetch CGI::Cookie();
my $cook = 'cookies=table([{';
foreach my $c (keys %cookies) {
    my $val=$cookies{$c}->value();
    $c =~ s/'/''/g; 
    $val =~ s/'/''/g;
    $cook .= "['$c',['$val']],";
}
$cook .= 'NULL';

$cook .= '}],unassigned)';
$cook =~ s/\r\n//sg;
$cook =~ s/\n//sg;

my $f = undef;
my @p = ();
my @a = ();
my $cache = undef;
my $session = undef;

if (not defined($req->param('f'))) {
    ($f,@p) = @ARGV;
#    print STDERR "using argv (@ARGV)\n";
}
else {
    $f = $req->param('f');
    if ($f =~/[^A-Za-z0-9_]/) { die "Malformed function request"; }
    
    if ($f eq "UploadData") {
        if ($session=param('session')) {
            # we have a returning user who is waiting for session data
            $cache = getCacheHandle();
            my $data = $cache->get($session);
            unless($data and ref $data eq "ARRAY"){
                open(ERRLOG,">>$error_log");
                print ERRLOG "session data invalid: $session\n";
                close(ERRLOG);
                delete_all();
		print header(-status=>500);
		print h1("Invalid session number");
		print p('Sorry, you will need to start over: <a href="'
		    . self_url() . '">home</a>');
                #print redirect(self_url());
                exit 0;
            }
            if ($data->[0] == 0){
                # still computing
                my $msg=$data->[1];
                show_waiting( $msg );
                print DBGLOG "[checker] not finished: ".$data->[0]."\n";
                exit 0;
            }
            elsif ($data->[0] == 1){
                @p = @{$data->[1][0]};
                @a = @{$data->[1][1]};
                print DBGLOG "[pickup] data loaded: [@p]  [@a]\n" if $debug;
            } 
            else {
                # error happend in conversion
                print header(-status=>500);
                print $data->[1];
                print end_html;
                open(ERRLOG, ">>$error_log"); print ERRLOG $data->[0].":".$data->[1]."\n"; close(ERRLOG);
                exit 0;
            }
        } 
        else {
            $session = getSessionId();
            $cache = getCacheHandle();
            $cache->set($session, [0,""]);

            if (my $pid = fork) {
                # parent process
                delete_all();
                param('session', $session);
                param('f','UploadData');
                print DBGLOG "[parrent] session is $session\n" if $debug;

                print redirect( self_url() );
                exit 0;
            } 
            elsif (defined $pid){
                # chlild process
                close STDOUT; # allows parent to go on
                open STDOUT, '>>', "$upload_log";

                print DBGLOG "[child] session is $session\n" if $debug;
                process_datafiles();
                print DBGLOG "[child] finished conversion of datafile" if $debug;
                close STDOUT;
                exit 0;
            } 
            else { die "cannot fork: $!";
            }
        }
    }
 

   
    if( $debug > 0 ){
        my @pa = $req->param();
	print DBGLOG "Parameters: @pa\n";
    }
    foreach my $m (sort($req->param)) {
        if ($m =~/^p([A-Za-z]*\d*)$/) {
            my $c = $req->param($m);
            # multiline input format
            $c =~ s/\r\n//sg;
            $c =~ s/\n//sg;
            $c =~ s/'//sg;
            # we add quotes if the parameters contains anything not a digit
            if ($c =~/[^0-9]/ or length($c) > 30)  {
                if ($c ne 'false' and $c ne 'true') { 
                    $c = "'".$c."'"; 
                }
            }
            push(@p,$c);
            push(@a,$m);
        }
    }
    print DBGLOG "passed parameters: @p\n" if $debug;
}

#die('No input whatsoever') unless defined($f);
if (not defined($f)) { $f = 'Index' }
print DBGLOG "Function call: $f\n" if $debug;

#### we verify that we have not just issed a "too busy" message
if (time - (stat('/tmp/BSbusy'))[9] < 10 and not $debug) { 
  die "The server is busy... please wait a few seconds and try again.\n" 
}

####################################################################
# we create an output file
my $id = $ENV{REMOTE_ADDR}.'.'.int(100000*rand());
#$id =~ s/\.//g; 
my $file = '/tmp/BS'.$id;
unlink($file);
unlink($file.'.alive');
# we do at most three trials
foreach (1..3) {
    mkfifo($file, 0666) and mkfifo($file.'.alive', 0666) and 
    chmod(0666,$file) and chmod(0666,$file.'.alive') and last;
    open(ERRLOG,">>$error_log");
    print ERRLOG "Error (gateway.pl): pipe files could not be created -- $!\n";
    close(ERRLOG);
    sleep(1);    
}
print DBGLOG "$file suc created: ". (-e $file)."\n" if $debug; 
if (not -e $file){
    open(ERRLOG,">>$error_log");
    print ERRLOG "Error (gateway.pl): $file does not exist.\n";
    close(ERRLOG);
}
if (not -e $file.'.alive'){
    open(ERRLOG,">>$error_log");
    print ERRLOG "Error (gateway.pl): $file.alive does not exist.\n";
    close(ERRLOG);
}
####################################################################

# we write the request to server pipe
open(REQ,'>>'.$pDarwin);
my $p = join(',',@p);
my $a = join(',',@a);
print REQ "Request($f,'$file'".($#p > -1 ? ",params=[$p]" : "") . 
   ($#a > -1 ? ",pnames=[$a]":"") . ",".$cook.");\n";
print "Request($f,'$file'".($#p > -1 ? ",params=[$p]" : "") . 
   ($#a > -1 ? ",pnames=[$a]":"") . ",".$cook.");\n"  if $debug;
close(REQ);


####################################################################
# We make sure that the server is alive 
$SIG{"ALRM"} = sub { 
    print header(-status=>500);
    print "Server too busy, please try again in a few minutes...\n"; 
    print $ENV{QUERY_STRING};
    unlink($file.'.alive'); 
    unlink($file);
    system("touch /tmp/BSbusy"); 
    exit;
};
alarm 20;
open(IN,$file.'.alive');
my @in = <IN>;
print DBGLOG "content of $file.alive:" . @in if $debug;
close(IN);
alarm 0;

####################################################################
# Wait for answer and print it
$SIG{"ALRM"} = sub { unlink($file); die "Request timed out...\n"; exit;};
## we read the result
alarm 120;
print DBGLOG "waiting for result from $file\n" if $debug;
open(IN,$file);
alarm 5;

# we now read the output until we have a line that only contains 'EOF'
my $sent_header = 0;
while (<IN>) {
    my $l = $_;
    # first we have to make sure that darwin is ALIVE
    if ($l =~/^EOF/) { last; }
    else {
        if (not $sent_header and ($l =~/^Location: /)) {
            $sent_header = 1;
	}
        elsif (not $sent_header and ($l =~/<.*html/i)) {
            print "Content-type: text/html; charset=iso-8859-1\n\n";
            $sent_header = 1;
        }
        elsif (not $sent_header) {
            print "Content-type: text/plain; charset=iso-8859-1\n\n";
            $sent_header = 1;
        }
    print "$l"; alarm(5);
    }
}
close(IN);

close(DBGLOG) if $debug;
unlink($file);
unlink($file.'.alive');


sub SeqFasta2Drw{
    my ($fh, $fnSeq, $fnSps, $p2s) = @_;
    
    my %sps = ();
    my $AA = "ACDEFGHIKLMNPQRSTVWXY";
    open(F,">$fnSeq") or die($!);
    open( RAW, ">$fnSeq.raw") or die($!) if $storeRaw; 

    my $cnt=0; my $err=0;
    while( <$fh> ){
        print RAW $_  if $storeRaw;
        chomp;
        if (/^>(\w[\w\.-_]*)(.*)/) {
	     my $spc = undef;
	     my $id = $1; my $headRest = $2;
	     
	     if ($p2s != 0 and defined $p2s->{$id}){ $spc=$p2s->{$id}; }
	     elsif ($headRest =~ /taxid:(\d+)/i) { $spc=$1;}
             elsif ($headRest =~ /\[(.+)\]/) { $spc=$1; }
	     elsif ($id =~ /_([A-Z][A-Z0-9]{2,4})/) {$spc=$1; }
             elsif ($id =~ /^([A-Z][A-Z0-9]{4})\d+/){$spc=$1; }
             elsif ($id =~ /^(ENS\w*)[G|P|T]\d+/) {$spc=$1;}
	     elsif ($headRest =~ /(ENS\w*)[G|P|T]\d+/) {$spc=$1;}
             else { $err++; };

             $sps{$spc}=1;
             print F "']:\n" if ($cnt>0);
             print F "Protein := ['$id','$spc','";
             $cnt++;
        }
	elsif (/^;/) {} # ignore comments 
        else { 
            uc;           # uppercase letters
	    s/\*$//;      # remove stop-codon symbol
            s/[^$AA]/X/g; # replace any non-amino by X
            print F;
        }
    }
    print F "']:\n";
    close(F);
    close(RAW) if $storeRaw;
    
    open(F, ">$fnSps") or die($!);
    print F "SPS := [\n";
    for my $k (keys( %sps )) { print F "'$k',\n"; }
    print F "NULL]:\n";
    close(F);

    return($cnt);
}




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
    $cache->set($session,[0,"processing orthoXML file. This may take a while, e.g. a 45Mb file requires roughly 20min to be processed"]);
    open( $relFh, ">$fn") or die("cannot open $fn for writing: $!");
    my $handler = OrthoXML->new($relFh);
    my $parser = XML::SAX::ParserFactory->parser(Handler => $handler);
    print "[$session] parser initialized, start parsing...\n";
    $parser->parse_file($fh) or die("can't parse: $!");
    print "[$session] ...finished parsing\n";
    close( $relFh );
    return( $handler->get_nr_of_relations());
}

sub RelText2Drw {
    my ($fh, $fn) = @_;
    
    my $cnt = 0;
    open(F,">$fn") or die($!);
    open( RAW, ">$fn.raw") or die($!) if $storeRaw; 
    print F "PairRelations([\n";
    while( <$fh> ){
        print RAW $_ if $storeRaw;
        chomp;
    if ( /([\w.-]*)\t([\w.-]*)/ ){
       print F "['$1','$2'],\n";
       $cnt++;
       if ($cnt % 50000 == 0){ print F "NULL]):\nPairRelations([\n";}
        }
    }
    print F "NULL]):\n";
    close(F);
    close(RAW) if $storeRaw;
    return($cnt);
}

sub RelCOG2Drw {
    my ($fh, $fn) = @_;

    my $cnts = 0; 
    my $state = 2;  #1: appending; 2: Ended
    my %p2s = {};
    my ($spec, $rowl);

    open(F, ">$fn");
    while( <$fh> ){
        chomp;
	next if ($_ eq '');

	# cog title
	if (/^\[(\w{1,6})\] (\w+) / and $state == 2){
	    $state = 1;
	    $rowl = 0;
	    print F "GroupRelations([\n";
        }
	# species entry
	elsif (/^ +(\w{3,5}): +(.+)/ and $state == 1){
	    $spec = $1;
	    foreach my $l ( split(/\s+/, $2) ){
                $p2s{$l} = $spec;
	        print F "'$l',";
	        print F "\n" if ( (++$rowl % 10)==0); 
	    }
	}
        # delimiter
	elsif (/\_{5}/ and $state==1){
	    print F "NULL]);\n";
	    $state = 2;
	    $cnts += ($rowl*($rowl-1)/2);
	}
	# multiline species
	elsif( /^\s{7,}(.+)/ ){
	    foreach my $l (split(/\s+/, $1)){
	        $p2s{$l} = $spec;
	        print F "'$l',";
	        print F "\n" if ( (++$rowl % 10)==0); 
            }
	}
    }
    close(F);
    open(F, ">/tmp/p2s.txt");
    foreach my $k (keys(%p2s)){
         print F $k." --> ".$p2s{$k}."\n";
    }
    return( ($cnts, \%p2s) );
}

sub show_waiting {
    my @content = @_;
    print header;
    print start_html(-title=>"Processing data",
                     -head=>["<meta http-equiv=refresh content=10>"]);
    print h1("Processing data");
    print escapeHTML(@content[0]);
    print p(i("... continuing ..."));
    print end_html;

}

sub process_datafiles{
    # store uploaded data
    my $methName = $req->param("methName");
    $methName =~ s/'/''/g; # make sure name is properly quoted

    my $fnBase = $req->param("methName");
    $fnBase =~ tr/ /_/;
    $fnBase =~ s/[^A-Za-z0-9_.-]//g;
    my $timestamp = ""; #strftime("%Y%m%d-%H%M", localtime());
    print DBGLOG "[worker] $fnBase - $timestamp\n" if $debug;
    $fnBase = "/local/BenchmarkService/projects/".$fnBase."-".$timestamp.
        ".".int(1000*rand());

    print DBGLOG "storing uploaded file with filenamebase $fnBase\n" if $debug;
    my $nrProt=0; my $nrOrth=0;
    my $prot2spec = 0;
    my $reference = $req->param("reference");

    foreach my $upFile ( qw(rels seqs) ){
        next if ($upFile eq "seqs" && $reference ne "OMA");

        if (!$req->param($upFile)) {
           my $msg = "Error (gateway.pl): A problem during the upload of your $upFile occured.\n";
           open(ERRLOG, ">>$error_log"); print ERRLOG $msg; close(ERRLOG);
           $cache->set($session, [-1, $msg] );
           exit;
        }
        
        $cache->set($session,[0,"saving ".$upFile." file"]);
        my $fn = "$fnBase.$upFile";
        my ($fileName,$path,$suffix) = fileparse($req->param($upFile),qr/\.(gz|bz2)/);
        my $fh = $req->upload($upFile);
        if (!$fh && cgi_error) {
            $cache->set($session, [-1, "CGI error: ".&cgi_error]);
            exit 0;
        }
        print "[$session] upload of ".$upFile." finished\n";
        $fh = $fh->handle;
        if ($suffix ne ""){
            open( my $decmpFh,  ">$fn.tmp");
            if ($suffix eq ".gz"){
                gunzip( $fh => $decmpFh) or die "gunzip failed: $GunzipError\n";
            } elsif ($suffix eq ".bz2"){
                bunzip2( $fh => $decmpFh) or die "bunzip2 failed: $Bunzip2Error\n";
            }
            close( $decmpFh );
            close( $fh );
            $fh = new IO::File("$fn.tmp", "r");
            print "[$session] decompression finished, fh reset\n";
        }
        if( $upFile eq "seqs"){
           if ($req->param("seqType") eq "fasta"){ $nrProt = SeqFasta2Drw($fh, $fn, $fnBase.".sps",$prot2spec);
           } elsif ($req->param("seqType") eq "xml"){ $nrProt = SeqXML2Drw($fh, $fn, $fnBase.".sps");
           } else {die("unknown seqType: ".$req->param("seqType"));}
        }
        else {
           if ($req->param("relType") eq "txt"){ $nrOrth = RelText2Drw($fh,$fn);
           } elsif ($req->param("relType") eq "xml"){ $nrOrth = RelXML2Drw($fh, $fn);
           } elsif ($req->param("relType") eq "cog"){ 
               ($nrOrth, $prot2spec) = RelCOG2Drw($fh, $fn);
           } else {die("unknown relType: ".$req->param("relType"));}
        }
        print DBGLOG "successfully uploaded $upFile into $fnBase.$upFile\n" if $debug;
        print "[$session] successfully uploaded $upFile into $fnBase.$upFile\n";
    }
    push(@p, "'".$fnBase."'", "'".$methName."'", $nrProt, $nrOrth, "'".$reference."'");
    push(@a, "'fnBase'", "'methName'", "'nrProt'", "'nrOrth'", "'reference'");
    $cache->set($session,[1,[\@p,\@a]]);
} 

sub getCacheHandle {
  require Cache::FileCache;

  Cache::FileCache->new
      ({
        namespace => 'BenchmarkService',
        username => 'nobody',
        default_expires_in => '48 hours',
        auto_purge_interval => '240 hours',
       });
}

sub getSessionId {
    require Digest::MD5;

    Digest::MD5::md5_hex(Digest::MD5::md5_hex(time().{}.rand().$$));
}

