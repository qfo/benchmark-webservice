#!/usr/bin/perl

use CGI qw/:standard delete_all/;
use CGI::Cookie;
use POSIX qw/mkfifo strftime/;
use CGI::Carp qw/carpout fatalsToBrowser set_message/;
use File::stat;
use File::Basename;
use File::Copy;
use IO::Zlib;
use IO::Uncompress::Bunzip2 qw(bunzip2 $Bunzip2Error);
use IO::Uncompress::Gunzip qw(gunzip $GunzipError);
use IO::Compress::Gzip qw(gzip $GzipError);
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
my $error_log = $ENV{"DARWIN_LOG_PATH"}.'/BS_gateway_error.log';
my $dbg_log = $ENV{"DARWIN_LOG_PATH"}.'/BS_gateway_debug.log';
my $upload_log = $ENV{"DARWIN_LOG_PATH"}.'/BS_upload.log';
my $MAXLOAD = 24;

# maximum Post size in bytes 
$CGI::POST_MAX = 1<<33;
$|++; # disable buffering of stdout

#use Time::HiRes qw(time);
my $hostname = `/bin/hostname`;
chomp($hostname);
my $din = 'BSin.'.$hostname;
my $pDarwin = $ENV{DARWIN_RUN_PATH}.'/'.$din;


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
#my $cache = undef;

# check whether server load is too high
my $sysload = (getSysLoad())[0];
if ($sysload > $MAXLOAD) {
    die "Server too busy, please try again in a few minutes...";
}


if (not defined($req->param('f'))) {
    ($f,@p) = @ARGV;
#    print STDERR "using argv (@ARGV)\n";
}
else {
    $f = $req->param('f');
    if ($f =~/[^A-Za-z0-9_]/) { die "Malformed function request"; }
    
    if ($f eq "UploadData") {
        if ($req->param("reference") eq "OMA"){
            print header(-status=>404);
            print h1("Reference Dataset \"OMA\" is no longer supported");
            print p('We do no longer support the reference dataset \"OMA\" anymore. Please use the QfO reference dataset instead. <a href="/">home</a>');
            exit 0;
        }
        print DBLOG "upload data" if $debug;
        process_datafiles();
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
            if ($c eq ''){
                $c = "''";
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
my $file = '/tmp/BS_outpipes/BS'.$id;
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

sub process_datafiles{
    # store uploaded data
    my $methName = $req->param("methName");
    $methName =~ s/'/''/g; # make sure name is properly quoted

    my $fnBase = $req->param("methName");
    $fnBase =~ tr/ /_/;
    $fnBase =~ s/[^A-Za-z0-9_.-]//g;
    my $timestamp = strftime("%Y%m%d-%H%M", localtime());
    print DBGLOG "[worker] $fnBase - $timestamp\n" if $debug;
    my $fnRoot = $ENV{DARWIN_ORTHOLOG_BENCHMARKDATA_PATH};
    my $fnProj = $fnRoot . "/projects";
    my $fnRawLnk = $fnRoot . "/htdocs/raw";
    $fnBase .= "-".$timestamp.".".int(1000*rand());

    my $vis = $req->param("methVis");
    if ($vis eq "public") {$vis="true"; }
    else { $vis="false";}

    my $methDesc = $req->param("methDesc");
    $methDesc =~ tr/'/"/;
    $methDesc =~ s/\n/<br\/>/g;

    my $methURL = $req->param("methURL");
    $methURL =~ s/([^?]*).*/\1/g;
    if ( $methURL !~ /^http:\/\// ){
        $methURL = "http://$methURL";
    }

    my $methEmail = $req->param("methEmail");
    my $email = "";
    if ( $methEmail =~ /([\w.-]+@[\w.-]+\.\w{2,})/ ){
        $email = $1
    } 

    print DBGLOG "storing uploaded file with fnBase $fnBase in $fnProj\n" if $debug;
    my $nrProt=0; my $nrOrth=0;
    my $prot2spec = 0;
    my $reference = $req->param("reference");

    foreach my $upFile ( qw(rels seqs) ){
        next if ($upFile eq "seqs"); 

        if (!$req->param($upFile)) {
           my $msg = "Error (gateway.pl): A problem during the upload of your $upFile occured.\nMost likely it was too big.";
           open(ERRLOG, ">>$error_log"); print ERRLOG $msg; close(ERRLOG);
           print header(-status=>500);
           print $msg;
           print end_html;
           exit;
        }

        my $fn = "$fnProj/$fnBase.$upFile";
        my ($fileName,$path,$suffix) = fileparse($req->param($upFile),qr/\.(gz|bz2)/);
        my $fh = $req->upload($upFile);
        if (!$fh && cgi_error) {
            die "CGI error: ".&cgi_error ;
            exit 0;
        }
        print DBGLOG "upload of ".$upFile." finished\n" if $debug;
        $fh = $fh->handle;
        
        open( my $upFh,  ">$fn.raw$suffix" );
        binmode $upFh;
        while (<$fh>){ print $upFh $_; }
        close($upFh);

        if ($suffix eq ""){
            gzip "$fn.raw" => "$fn.raw.gz" or die "gzip failed: $GzipError\n";
            $suffix = ".gz"
        }
        
        print DBGLOG "successfully uploaded $upFile into $fnBase.$upFile\n" if $debug;
        my $lnkFn = "$fnRawLnk/$fnBase.$upFile.raw.gz";
        my $status = eval{ symlink( "$fn.raw$suffix", "$lnkFn" ); 1 };
        if (not $status){
            copy( "$fn.raw$suffix", "$lnkFn") or die "symlinking and copying failed for $fn.raw$suffix to $lnkFn: $!\n";
        }
    }
    push(@p, "'$fnProj/$fnBase'", "'".$methName."'", $nrProt, $nrOrth, "'".$reference."'", $vis, "'".$methDesc."'","'".$methURL."'", "'".$email."'");
    push(@a, "'fnBase'", "'methName'", "'nrProt'", "'nrOrth'", "'reference'","'isPublic'","'methDesc'","'methURL'","'email'");
}


sub getSysLoad {
    my $fh = new IO::File('/proc/loadavg', 'r');
    if (defined $fh) {
        my $line = <$fh>;
        $fh->close();
        if ($line =~ /^(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)/) {
            return ($1, $2, $3);
        }  # if we can parse /proc/loadavg contents
    }
    chomp( my $sysload = `uptime`);
    if ($sysload =~ /load average: ([\d.]+),\s([\d.]+),\s([\d.]+)/){
        print "slow version\n" if $debug;
        return( $1, $2, $3 )
    } else {
        die("Cannot find out system load");
    }
}

