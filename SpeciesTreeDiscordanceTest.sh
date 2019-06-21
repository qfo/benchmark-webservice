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

  -c    confidence filter for the species tree levels. Currently fixed to 81, which
        means all the undisputed nodes in the literature.

  -t    treebuilding method. so far LSTree and BIONJ are available. Defaults to
        LSTree if not specified

  -o    output directory, where result.json and raw data file will be stored.
        Raw data is a file that contains the evaluated orthologs and their
        similarity score. The filename of raw data is available in the
        result.json file

  -a    option to select between different flavors of the species tree discordance
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
out_dir="STD"
confidence="81"
treebuilder="LSTree"
algo="SpeciesTreeDiscordanceTest.drw"

while getopts "c:o:p:t:a:h" opt ; do
    case $opt in
        h) usage
            exit 0
            ;;
        c) confidence="$OPTARG"
           ;;
        p) problem="$OPTARG"
           ;;
        t) treebuilder="$OPTARG"
           ;;
        o) out_dir="$OPTARG"
           ;;
        a) if [[ "$OPTARG" == "1" ]] ; then
              algo="SpeciesTreeDiscordanceTest-fixedsize.drw"
           elif [[ "$OPTARG" != "0" ]] ; then
              usage
              exit 1
           fi
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

if [ ! -d "$out_dir" ] ; then mkdir -p "$out_dir"; fi

darwin -E  << EOF
   project_db := '$project_db';
   problem := '$problem';
   confidence := $confidence;
   treebuilder := '$treebuilder';
   title := '$title';
   refset_path := '$refset';
   out_dir := '$out_dir';
   ReadProgram('$benchmark_dir/lib/darwinit');
   ReadProgram('$benchmark_dir/$algo');
   done;
EOF

