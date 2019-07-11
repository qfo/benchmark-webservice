#!/usr/bin/env nextflow


if (params.help) {
    log.info """
    ===========================================
      QFO ORTHOLOGY BENCHMARKING PIPELINE
    ===========================================
    Usage:
    Run the pipeline with default parameters:
    nexflow run benchmark.nf

    Run with user parameters:
    nextflow run benchmark.nf --predictions_file {orthology.predictions} --participant_name {tool.name} --results_dir {results.dir}

    Mandatory arguments:
        --predictions_file      Predicted orthologs in TSV or orthoxml file

        --participant_name      Name of the tool / method


    Additional options:
        --challenges_ids        List of benchmarks / challenges to be run by the pipeline.
                                Defaults to all available benchmarks

        --event_year            QfO Reference Proteomes release, defaults to 2018

        --community_id          Name or OEB permanent ID for the benchmarking community

        --go_evidences          Evidence filter of GO annotation used in the GO benchmark
                                Defaults to experimental annotations

        --results_dir           Base result for all the following output directories, unless overwritten
        --validation_result     The output directory where the results from validation step will be saved¬
        --assessment_results    The output directory where the results from the computed metrics step will be saved¬
        --aggregation_results   The output directory where the consolidation of the benchmark will be saved¬
        --statistics_results    The output directory with nextflow statistics¬
        --data_model_export_dir The output dir where json file with benchmarking data model contents will be saved¬
        --other_dir             The output directory where custom results will be saved (no directory inside)¬

    Flags:
        --help                  Display this message¬
    """.stripIndent()

    exit 1
}

log.info """
         ==============================================
          QFO ORTHOLOGY BENCHMARKING PIPELINE
         ==============================================
         input file: ${params.predictions_file}
         method name : ${params.participant_name}
         refeset path: ${params.refset}
         benchmarking community = ${params.community_id}
         selected benchmarks: ${params.challenges_ids}
         Evidence filter for GO benchmark: ${params.go_evidences}
         validation results directory: ${params.validation_result}
         assessment results directory: ${params.assessment_results}
         consolidated benchmark results directory: ${params.aggregation_results}
         Statistics results about nextflow run: ${params.statistics_results}
         Benchmarking data model file location: ${params.data_model_export_dir}
         Directory with community-specific results: ${params.other_dir}
         """
    .stripIndent()


//input
predictions = file(params.predictions_file)
method_name = params.participant_name
refset_dir = params.refset
benchmarks = params.challenges_ids
community_id = params.community_id
go_evidences = params.go_evidences
tree_clades = Channel.from("Luca", "Vertebrata", "Fungi", "Eukaryota")
genetree_sets = Channel.from("SwissTrees", "SemiAuto")
tree_clades0 = Channel.from("Eukaryota", "Fungi", "Bacteria")

//output
validation_out = file(params.validation_result)
assessment_out = file(params.assessment_results)
aggregation_dir = file(params.aggregation_results)
data_model_export_dir = file(params.data_model_export_dir)
other_dir = file(params.other_dir)


/*
 * validate input file
 */
process validate_input_file {
    label "py"

    input:
    file predictions
    val refset_dir
    val benchmarks
    val community_id
    val method_name
    val validation_out

    output:
    val task.exitStatus into EXIT_STAT

    """
    /benchmark/validate.py --com $community_id --challenges_ids "$benchmarks" --participant "$method_name" --out $validation_out $refset_dir/mapping.json.gz $predictions
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
    val clade from tree_clades0

    output:
    file "STD_$clade"


    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "STD_$clade" -p $clade $db "$method_name" $refset_dir
    """
}

process g_speciestree_benchmark {

    label "darwin"
    publishDir "${params.results_dir}", mode: 'copy', overwrite: true

    input:
    file db from db
    val method_name
    val refset_dir
    val clade from tree_clades

    output:
    file "G_STD_$clade"


    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "G_STD_$clade" -p $clade -a 1 $db "$method_name" $refset_dir
    """
}

process g_speciestree_benchmark_variant2 {
    label "darwin"
    publishDir "${params.results_dir}", mode: 'copy', overwrite: true

    input:
    file db from db
    val method_name
    val refset_dir

    output:
    file "G_STD2_Luca"

    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -a 2 -o G_STD2_Luca -p Luca $db "$method_name" $refset_dir
    """
}


process reference_genetrees_benchmark {
    label "darwin"
    publishDir "${params.results_dir}", mode: 'copy', overwrite: true

    input:
    file db from db
    val method_name
    val refset_dir
    val testset from genetree_sets

    output:
    file "RefPhylo_$testset"

    """
    /benchmark/RefPhyloTest.sh -o "RefPhylo_$testset" -t "$testset" $db "$method_name" $refset_dir
    """
}


workflow.onComplete {
	println ( workflow.success ? "Done!" : "Oops .. something went wrong" )
}
