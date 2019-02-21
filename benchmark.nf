#!/usr/bin/env nextflow

params.in = "$basedir/upload/predictions.txt"
predictions = file(params.in)

/*
 * extract pairwise predicitons and store in darwin compatible database
 */
process convertPredictions {

    input: 
    file 'prediction' from predictions

    output:
    file "/method/predictions.db" into db

    """
    python3 map_relations.py --out /method/predictions.db /refset/mapping.json.gz prediction
    """
}


process go_benchmark {
    container: 'darwin:latest'

    input:
    file method from db

    output:
    /method/GO/stdout.log, /method/GO/result.json, /method/GO/raw_data.txt.gz

    """
    GoTest.sh file 'project-name'
    """
}
