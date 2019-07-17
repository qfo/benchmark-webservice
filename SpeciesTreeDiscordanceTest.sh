#!/bin/bash

usage(){
    cat << EOF
$0 - run SpeciesTree Discordance benchmark

Compute benchmark results for the species tree discordance benchmark for a single
orthology method. You can specify the reference dataset, evidence filters
and similarity measure using the below options. With the -a option, one can
select between the different flavors, i.e. original species tree discordance
benchmark, the generalized version and the improved generalized version.

Options

  -p    problem to analyse, one of the following caldes: Luca, Eukaryota,
        Fungi or Vertebrata

  -f    confidence filter for the species tree levels. Currently fixed to 81, which
        means all the undisputed nodes in the literature.

  -t    treebuilding method. so far LSTree and BIONJ are available. Defaults to
        LSTree if not specified

  -o    output directory, where raw data file will be stored.
        Raw data is a file that contains the evaluated orthologs and their
        similarity score.

  -a    assessment directory, where the assessemnt json stub will be stored

  -c    community_id, Name or OEB permanent ID for the benchmarking community

  -m    option to select between different flavors of the species tree discordance
        benchmark. The argument expects a numeric value between 0 and 2, where as 0
        is the default value and corresponds to the initial SpeciesTreeDiscordance
        benchmark. With 1, the Generalized SpeciesTreeDiscordance benchmark is
        selected and with 2, a newer, more uniform species sampling approach for the
        Generalized SpeciesTreeDiscordance benchmark is used.


Positional arguments:
  project_db   Path to project database

  title        Name of the project

  refset       Path to refset data

EOF
}

problem="Luca"
out_dir=""
assessment_dir=""
community_id="QfO"
confidence="81"
treebuilder="LSTree"
algo="TreeTest.drw"

while getopts "a:c:f:m:o:p:t:h" opt ; do
    case $opt in
        h) usage
            exit 0
            ;;
        f) confidence="$OPTARG"
           ;;
        p) problem="$OPTARG"
           ;;
        t) treebuilder="$OPTARG"
           ;;
        o) out_dir="$OPTARG"
           ;;
        m) if [[ "$OPTARG" == "2" ]] ; then
              algo="SpeciesTreeDiscordanceTest-fixedsize.drw"
           elif [[ "$OPTARG" == "1" ]] ; then
              algo="SpeciesTreeDiscordanceTest.drw"
           elif [[ "$OPTARG" != "0" ]] ; then
              usage
              exit 1
           fi
           ;;
        a) assessment_dir="$OPTARG"
           ;;
        c) community_id="$OPTARG"
           ;;
        \?)  echo "invalid option" >&2
           usage
           exit 1
           ;;
        :) echo "option -$OPTARG requires an argument" >&2
           usage
           exit 1
           ;;
    esac
done
shift $((OPTIND-1))
echo $@

project_db="$1"
if [ ! -f $project_db ] ; then
    echo "invalid path to project_database" >&2
    exit 1
fi
title="$2"
refset="$3"
benchmark_dir="$(dirname $0)"

if [[ -z "$out_dir" || -z "$assessment_dir" ]]; then
    echo "output and assessment directories are mandatory arguments"
    exit 1
fi
if [ ! -d "$out_dir" ] ; then mkdir -p "$out_dir"; echo "created $out_dir"; fi
if [ ! -d "$assessment_dir" ] ; then mkdir -p "$assessment_dir"; echo "created $assessment_dir"; fi

darwin -E  << EOF
   project_db := '$project_db';
   problem := '$problem';
   confidence := $confidence;
   treebuilder := '$treebuilder';
   title := '$title';
   refset_path := '$refset';
   out_dir := '$out_dir';
   assessment_dir := '$assessment_dir';
   community_id := '$community_id';
   ReadProgram('$benchmark_dir/lib/darwinit');
   res := traperror(ReadProgram('$benchmark_dir/$algo'));
   if res = lasterror then
       exit(1);
   fi:
   done
EOF

