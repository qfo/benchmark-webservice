#!/bin/bash

usage(){
    cat << EOF
$0 - run Gene Ontology benchmark

Compute benchmark results for the Gene Ontology benchmark for a single 
orthology method. You can specify the reference dataset, evidence filters
and similarity measure using the below options

Options 

  -m    similarity measure. Can be one of 'avg Sim', 'max Sim', 'avg Info',
        'max Info' or 'avg Schlicker'

  -e    evidence filter for GO annotations to be considered in benchmark. The 
        value can either be a list of evidences, e.g. "[IPI,IEA,IDA]" or one 
        of the three following evidence shortcuts:
          - exp: all non-highthroughput experimental evidence codes, i.e.
                 EXP, IDA, IPI, IMP, IGI, IEP

          - cur: all non-electronic annotations, except ND (no biological data)

          - all: all annotations, including those with IEA and ND evidence code

        If not evidence filter is set, it defaults to the experimental codes.

  -o    output directory, where the raw data file will be stored.
        Raw data is a file that contains the evaluated orthologs and their
        similarity score.

  -a    assessment filename, where the assessemnt json stub will be stored

  -c    community_id, Name or OEB permanent ID for the benchmarking community


Positional arguments:
  project_db   Path to project database
  
  title        Name of the project

  refset       Path to refset data

EOF
}

measure="avg Schlicker"
out_dir=""
assessment_fname="GO.json"
community_id="QfO"
evidences="exp"
while getopts "a:c:e:m:o:h" opt ; do
    case $opt in
        h) usage
            exit 0
            ;;
        m) measure="$OPTARG"
           if [[ $measure != "avg Sim" && $measure != "max Sim" && $measure != "avg Info" && \
                 $measure != "max Info" && $measure != "avg Schlicker" ]] ; then
              echo "invalid similarity measure" >&2
              exit 1
           fi
           ;;
        e) evidences="$OPTARG"
           if [[ $evidences != "exp" && $evidences != "cur" && $measure != "all" ]] ; then
               if [[ ${evidences:0:1} != '[' || ${evidences: -1} != ']' ]] ; then
                   echo "invalid evidence filter" >&2
                   exit 1
               fi
           else
               evidences="'$evidences'"
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

if [[ -z "$out_dir"  ]]; then
    echo "output directories is mandatory arguments"
    exit 1
fi
if [ ! -d "$out_dir" ] ; then mkdir -p "$out_dir"; echo "created $out_dir"; fi

darwin -E  << EOF
   project_db := '$project_db':
   measure := '$measure':
   evidences := $evidences:
   title := '$title':
   refset_path := '$refset':
   datadirname := '$refset':
   out_dir := '$out_dir':
   assessment_fname := '$assessment_fname':
   community_id := '$community_id':
   ReadProgram('$benchmark_dir/lib/darwinit');
   ReadProgram('$benchmark_dir/GoTest.drw');
   done;
EOF
exit $?
