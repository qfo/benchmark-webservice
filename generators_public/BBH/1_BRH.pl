#Use with 1_BRH_job
#cecile pereira
#10 janv 2016
#aim: extract informations from the blastp
#results: ID, best hits, lenght of the alignment and score

#perl 1_BRH.pl [working repertory] [blastp repertory]

$dirOUT=$ARGV[0].'/BH/';
mkdir($dirOUT) unless (-e $dirOUT);

opendir(BL,$ARGV[1])or die;
@fb=readdir(BL);
closedir(BL);

foreach $b(@fb){
	unless(($b eq ".") || ($b eq "..")){
		print $b."\n";
		$nfs="BH_".$b;
		$nfs=~s/blast$/tab/;
		unless(-e $dirOUT.'/'.$nfs){
		    unless($b=~/(.+)_($1)\.blast/){#blast d'une espece contre elle meme
			system("perl 1_BRH_job.pl $ARGV[1]/$b $dirOUT $nfs");
		    }
		}
	}
}
