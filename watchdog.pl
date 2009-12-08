#!/usr/bin/perl
use POSIX qw(mkfifo);

# The watchdog runs every minute and makes sure that
#  a) web and darwin server are up and running
#     - retrieve the server pid in /tmp/omapid and check the status of that pid
#     - retrieve the 
#  b) memory/cpu usage of server are not too high

$wdir = '/local/Browser/';
$MemLimit = $hostname eq 'linneus54' ? '3e10' : '8e5'; # kilobytes
$hostname = `/bin/hostname`;
chomp($hostname);
$din = 'BSin.'.$hostname;

@p=(    
#        {	name => 'Web Server',
#		command => $wdir . '/lighttpd/sbin/lighttpd -f '.$wdir.'/lighttpd/conf/lighttpd.conf',
#		pid => '/tmp/lighttpd.pid',
#	},
	{
		name => 'Darwin Server',
		command => "$wdir/startserver.".($hostname eq 'linneus54' ? 'linneus54.':'')."csh",
		pid => "$wdir/omapid.$hostname",
	},
	#{
#		name => 'test',
#		command => 'echo joy',
#		pid => '19531'
#	}
);


# we verify that we have an input pipe for darwin
mkfifo('/tmp/'.$din, 0666) or die "Can't create FIFO" unless (-p '/tmp/'.$din);


foreach $p (@p) {
        $comm = "/bin/cat ".$p->{pid};
	if (-e $p->{pid} and `$comm` =~/^(\d+)$/) {
		$pid=$1;
		# verify usage is reasonable
		#print "ps -o rss,%cpu,%mem -p $pid | grep -v RSS\n";
		print $p->{name} . "'s pid is defined: $pid\n";
		$lsof = `/usr/sbin/lsof | grep $pid | grep Din`;
		@ps = split(/\s+/,`/bin/ps -o rss,%cpu,%mem,stat -p $pid | grep -v RSS`);
                #print  time - (stat($wdir.'/omapid.'.$hostname))[9];
		if (defined($ps[0])) {
			# it is running fine
			print $p->{name} . " is running fine!\n";
		}
		else {
			print $p->{name} . " is not running. Starting!\n";
			system($p->{command});
		}
	}
	else {
		print $p->{name} . " has no pid to be found. Starting!\n";

		system($p->{command});
		
	}
}

print "cleaning up /tmp/....\n";
system("find /tmp/ -maxdepth 1 -name \"[0-9.]*\" -mtime +1 -exec rm {} \\; ");
system("find /tmp/ -maxdepth 1 -name \"*.alive\" -mtime +1 -exec rm {} \\; ");
system("find /tmp/ -maxdepth 1 -name \"Browser-MSA*\" -mtime +5 -exec rm {} \\; ");
