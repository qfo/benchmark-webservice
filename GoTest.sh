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

  -o    filename of the raw output, i.e. the evaluated orthologs and their 
        similarity score. Defaults to GO/<name>-tba.txt.gz'

Positional arguments:
  prject_db   Path to prject database
  
  title       Name of the project

EOF
}

measure="avg Schlicker"
raw_out="GO/raw.txt.gz"
while getopts "m:o:h" opt ; do
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
        o) raw_out="$OPTARG"
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


darwin -E  << EOF
   project_db := '$project_db':
   measure := '$measure':
   filter := ['EXP']:
   title := '$title':
   ReadProgram('GoTest.drw');
   done;
EOF

