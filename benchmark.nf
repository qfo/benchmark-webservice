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
genetree_sets = Channel.from("SwissTrees", "TreeFam-A")
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

    input:
    file db from db
    val method_name
    val refset_dir
    val go_evidences
    val community_id
    val assessment_out
    val other_dir
    // for mountpoint 
    file predictions


    """
    /benchmark/GoTest.sh -o "$other_dir" -a "$assessment_out" -c "$community_id" -e "$go_evidences" $db "$method_name" $refset_dir
    """
}

process ec_benchmark {

    label "darwin"

    input:
    file db from db
    val method_name
    val refset_dir
    val community_id
    val assessment_out
    val other_dir
    // for mountpoint 
    file predictions


    """
    /benchmark/EcTest.sh -o "$other_dir" -a "$assessment_out" -c "$community_id" $db "$method_name" $refset_dir
    """
}


process speciestree_benchmark {

    label "darwin"

    input:
    file db from db
    val method_name
    val refset_dir
    val clade from tree_clades0
    val community_id
    val assessment_out
    val other_dir
    // for mountpoint 
    file predictions


    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "$other_dir" -a "$assessment_out" -c "$community_id" -p $clade -m 0 $db "$method_name" $refset_dir
    """
}

process g_speciestree_benchmark {

    label "darwin"

    input:
    file db from db
    val method_name
    val refset_dir
    val clade from tree_clades
    val community_id
    val assessment_out
    val other_dir
    // for mountpoint 
    file predictions


    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "$other_dir" -a "$assessment_out" -c "$community_id" -p $clade -m 1 $db "$method_name" $refset_dir
    """
}

process g_speciestree_benchmark_variant2 {
    label "darwin"

    input:
    file db from db
    val method_name
    val refset_dir
    val community_id
    val assessment_out
    val other_dir
    // for mountpoint 
    file predictions


    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "$other_dir" -a "$assessment_out" -c "$community_id" -p Luca -m 2 $db "$method_name" $refset_dir
    """
}

/* not yet ready
process reference_genetrees_benchmark {
    label "darwin"
    publishDir "${params.results_dir}", mode: 'copy', overwrite: true

    input:
    file db from db
    val method_name
    val refset_dir
    val testset from genetree_sets
    val community_id
    val assessment_out
    val other_dir
    // for mountpoint 
    file predictions


    """
    /benchmark/RefPhyloTest.sh -o "$other_dir" -a "$assessment_dir" -t "$testset" $db "$method_name" $refset_dir
    """
}

process consolidate {
    label "py"

    input:
    file go_assessment
    file ec_assessment
    file std from std_assessments.collect()
    file g_std from g_std_assessments.collect()
    file g_std2_assessment
    file validation_out
    val assessment_out
    val data_model_export_dir
    //for mountpoint
    file predictions

    """
    python /benchmark/merge_data_model_files.py -p "$validation_out" -m "$assessment_out" -a "$assessment_out" -o "$data_model_export_dir"
    """
}

*/


workflow.onComplete {
	println ( workflow.success ? "Done!" : "Oops .. something went wrong" )
}
