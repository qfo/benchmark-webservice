#!/bin/bash

usage(){
    cat << EOF
$0 - run Reference Phylogeny benchmark

Compute benchmark results for the Reference Phylogeny benchmark for a
single orthology method. You can specify the reference dataset and the
testset using the below options

Options 
  -t    testset, currently accepted are either SwissTree or TreeFam-A.

  -o    output directory, where raw data file will be stored.
        Raw data is a file that contains the implied pairwise relations of
        the testset's gene families and the correctness label according to
        the provided orthology predictions. The filename of raw data is
        available in the result.json file

  -a    assessment filename, where the assessemnt json stub will be stored

  -c    community_id, Name or OEB permanent ID for the benchmarking community

Positional arguments:
  project_db   Path to project database
  
  title        Name of the project

  refset       Path to refset data

EOF
}

testset="SwissTrees"
out_dir=""
assessment_fname=""
community_id="QfO"
while getopts "a:c:t:o:h" opt ; do
    case $opt in
        h) usage
            exit 0
            ;;
        t) testset="$OPTARG"
           if [[ $testset != "SwissTrees" && $testset != "TreeFam-A" ]] ; then
              echo "invalid testset option" >&2
              exit 1
           fi
           ;;
        o) out_dir="$OPTARG"
           ;;
        a) assessment_fname="$OPTARG"
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

if [[ -z "$out_dir" || -z "$assessment_fname" ]]; then
    echo "output and assessment are mandatory arguments"
    exit 1
fi
if [ ! -d "$out_dir" ] ; then mkdir -p "$out_dir"; echo "created $out_dir"; fi

darwin -E << EOF
   project_db := '$project_db':
   testset := '$testset':
   title := '$title':
   refset_path := '$refset':
   out_dir := '$out_dir':
   assessment_fname := '$assessment_fname':
   community_id := '$community_id':
   ReadProgram('$benchmark_dir/lib/darwinit');
   ReadProgram('$benchmark_dir/RefPhyloTest.drw');
   exit(1);
EOF

exit $?