#!/usr/bin/env nextflow

log.info """ \
		   QfO Benchmark at OpenEBench
      =============================
         input file: ${params.predictions_file}
         method name : ${params.participant_name}
         refeset path: ${params.refset}
         results directory: ${params.results_dir}

         GO benchmark:
            evidence filter: ${params.go_evidences}

         """
.stripIndent()

predictions = file(params.predictions_file)
method_name = params.participant_name
refset_dir = params.refset
result = file(params.results_dir)
go_evidences = params.go_evidences

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
    publishDir path: "${params.results_dir}", mode: 'copy', overwrite: true

    input:
    file db from db
    val method_name
    val refset_dir
    val go_evidences

    output:
    file "GO"


    """
    /benchmark/GoTest.sh -o "GO" -e "$go_evidences" $db "$method_name" $refset_dir
    """
}

process ec_benchmark {

    label "darwin"
    publishDir "${params.results_dir}", mode: 'copy', overwrite: true

    input:
    file db from db
    val method_name
    val refset_dir

    output:
    file "EC"


    """
    /benchmark/EcTest.sh -o "EC" $db "$method_name" $refset_dir
    """
}

process speciestree_benchmark {

    label "darwin"
    publishDir "${params.results_dir}", mode: 'copy', overwrite: true

    input:
    file db from db
    val method_name
    val refset_dir

    output:
    file "STD_Luca"


    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "STD_Luca" -p Luca $db "$method_name" $refset_dir
    """
}


workflow.onComplete {
	println ( workflow.success ? "Done!" : "Oops .. something went wrong" )
}
