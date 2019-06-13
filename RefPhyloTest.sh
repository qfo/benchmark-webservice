#!/bin/bash

usage(){
    cat << EOF
$0 - run Reference Phylogeny benchmark

Compute benchmark results for the Reference Phylogeny benchmark for a
single orthology method. You can specify the reference dataset and the
testset using the below options

Options 
  -t    testset, currently accepted are either SwissTree or SemiAuto.

  -o    output directory, where result.json and raw data file will be stored.
        Raw data is a file that contains the implied pairwise relations of
        the testset's gene families and the correctness label according to
        the provided orthology predictions. The filename of raw data is
        available in the result.json file

Positional arguments:
  project_db   Path to project database
  
  title        Name of the project

  refset       Path to refset data

EOF
}

testset="SwissTrees"
while getopts "t:o:h" opt ; do
    case $opt in
        h) usage
            exit 0
            ;;
        t) testset="$OPTARG"
           if [[ $testset != "SwissTrees" && $testset != "SemiAuto" ]] ; then
              echo "invalid testset option" >&2
              exit 1
           fi
           ;;
        o) out_dir="$OPTARG"
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
   project_db := '$project_db':
   testset := '$testset':
   title := '$title':
   refset_path := '$refset':
   out_dir := '$out_dir':
   ReadProgram('$benchmark_dir/lib/darwinit');
   ReadProgram('$benchmark_dir/RefPhyloTest.drw');
   done
EOF

