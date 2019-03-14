#!/usr/bin/env nextflow

log.info """ \
		   QfO Benchmark at OpenEBench
      =============================
         input file: ${params.predictions_file}
         method name : ${params.participant_name}
         refeset path: ${params.refset}
         results directory: ${params.results_dir}
         """
.stripIndent()

predictions = file(params.predictions_file)
method_name = params.participant_name
refset_dir = params.refset
result = file(params.results_dir)


/*
 * validate input file
 */
process validate_input_file {
    label "py"

    input:
    file predictions
    val refset_dir

    output:
    val task.exitStatus into EXIT_STAT

    """
    /benchmark/validate.py $refset_dir/mapping.json.gz $predictions
    """
}

/*
 * extract pairwise predictions and store in darwin compatible database
 */
process convertPredictions {

    label "py"

    input:
    val file_validated from EXIT_STAT
    file predictions
    val refset_dir

    output:
    file 'predictions.db' into db

    when:
    file_validated == 0

    """
    /benchmark/map_relations.py --out predictions.db $refset_dir/mapping.json.gz $predictions
    """
}


process go_benchmark {

    label "darwin"

    input:
    file db from db
    val method_name
    val refset_dir
    //val result


    """
    /benchmark/GoTest.sh -o "GO" $db "$method_name" $refset_dir
    """
}

process ec_benchmark {

    label "darwin"

    input:
    file db from db
    val method_name
    val refset_dir
    //val result


    """
    /benchmark/EcTest.sh -o "EC" $db "$method_name" $refset_dir
    """
}


workflow.onComplete {
	println ( workflow.success ? "Done!" : "Oops .. something went wrong" )
}
