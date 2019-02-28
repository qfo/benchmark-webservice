#!/usr/bin/env nextflow

predictions = file(params.predictions_file)
method_name = params.participant_name
refset_dir = params.refset
result = file(params.results_dir)


/*
 * extract pairwise predictions and store in darwin compatible database
 */
process convertPredictions {

    label "py"

    input: 
    file predictions

    output:
    file 'predictions.db' into db

    """
    /benchmark/map_relations.py --out predictions.db $refset_dir/mapping.json.gz $predictions
    """
}


process go_benchmark {

    label "darwin"

    input:
    file db from db

    output:
    file "GO/result.json"
    file "GO/raw_data.txt.gz"

    """
    /benchmark/GoTest.sh $db $method_name
    """
}
