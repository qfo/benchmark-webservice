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
    nextflow run benchmark.nf --input {orthology.predictions} --participant_id {tool.name} --results_dir {results.dir}

    Mandatory arguments:
        --input                 Predicted orthologs in TSV or orthoxml file

        --participant_id        Name of the tool / method


    Additional options:
        --challenges_ids        List of benchmarks / challenges to be run by the pipeline.
                                Separate challenges with space, and don't forget to quote.
                                Defaults to all available benchmarks:
                                "${params.challenges_ids}"

        --event_year            QfO Reference Proteomes release, defaults to 2018

        --community_id          Name or OEB permanent ID for the benchmarking community

        --go_evidences          Evidence filter of GO annotation used in the GO benchmark
                                Defaults to experimental annotations

        --goldstandard_dir      Dir that contains the benchmarking datasets needed to execute
        --assess_dir            Dir where the result data for the benchmark are stored (e.g. outdir of previous runs)

        --results_dir           Base result for all the following output directories, unless overwritten
        --validation_result     The output directory where the results from validation step will be saved (currently not used)
        --assessment_results    The output directory where the results from the computed metrics step will be saved
        --outdir                The output directory where the consolidation of the benchmark will be saved
        --statsdir              The output directory with nextflow statistics
        --data_model_export_dir The output dir where json file with benchmarking data model contents will be saved
        --otherdir              The output directory where custom results will be saved (no directory inside)

    Flags:
        --help                  Display this message¬
        --cpy_sqlite_db         Store the sqlite3 database with the pairwise prediction in the folder specified
                                with --otherdir parameter (${params.otherdir})
    """.stripIndent()

    exit 1
}

log.info """
         ==============================================
          QFO ORTHOLOGY BENCHMARKING PIPELINE
         ==============================================
         input file: ${params.input}
         method name : ${params.participant_id}
         goldstandard path (refset): ${params.goldstandard_dir}
         benchmarking community = ${params.community_id}
         selected benchmarks: ${params.challenges_ids}
         Evidence filter for GO benchmark: ${params.go_evidences}
         Public Benchmark results: ${params.assess_dir}
         validation results directory: ${params.validation_result}
         assessment results directory: ${params.assessment_results}
         consolidated benchmark results directory: ${params.outdir}
         Statistics results about nextflow run: ${params.statsdir}
         Benchmarking data model file location: ${params.data_model_export_dir}
         Directory with community-specific results: ${params.otherdir}
         """
    .stripIndent()


//input
predictions = file(params.input)
method_name = params.participant_id.replaceAll("\\s","_")
refset_dir = file(params.goldstandard_dir, type: 'dir')
benchmarks = params.challenges_ids
benchmarks_chan = Channel.from(params.challenges_ids.split(/ +/))
community_id = params.community_id
benchmark_data = file(params.assess_dir, type: 'dir')
go_evidences = params.go_evidences
tree_clades = ["Luca", "Vertebrata", "Fungi", "Eukaryota"]
tree_clades2 = ["Luca", "Vertebrata", "Fungi", "Eukaryota"]
genetree_sets = ["SwissTrees", "TreeFam-A"]
tree_clades0 = ["Eukaryota", "Fungi", "Bacteria"]

//output
//validation_out = file(params.validation_result)
assessment_out = file(params.assessment_results)
result_file_path = file(params.outdir, type: 'dir')
data_model_export_dir = file(params.data_model_export_dir)
otherdir = file(params.otherdir, type: 'dir')

// create output directories
assessment_out.parent.mkdirs()
result_file_path.mkdirs()
data_model_export_dir.parent.mkdirs()
otherdir.mkdirs()


/*
 * validate input file
 */
process validate_input_file {
    label "py"

    input:
    path predictions
    path refset_dir
    val benchmarks
    val community_id
    val method_name

    output:
    val task.exitStatus into EXIT_STAT
    path "participant.json" into PARTICIPANT_STUB

    """
    /benchmark/validate.py --com $community_id --challenges_ids "$benchmarks" --participant "$method_name" --out "participant.json" $refset_dir/mapping.json.gz $predictions
    """
}

// These channels rule next steps
db_go_test = Channel.create()
db_ec_test = Channel.create()
db_std = Channel.create()
db_g_std = Channel.create()
db_g_std_v2 = Channel.create()
db_geneTrees = Channel.create()
db_sp = Channel.create()
db_vgnc = Channel.create()
db_fas = Channel.create()

predictions_db = Channel.create()
sqlite_db = Channel.create()

predictions_db.into(db_go_test, db_ec_test, db_std, db_g_std, db_g_std_v2, db_geneTrees)
sqlite_db.into(db_sp, db_vgnc, db_fas)

/*
 * extract pairwise predictions and store in darwin compatible database
 */
process convertPredictions {

    label "py"
    publishDir path: "$otherdir", saveAs: {file -> (file == 'orthologs.db') ? "${method_name}.db" : null}, mode: "copy", enabled: params.cpy_sqlite_db

    input:
    val file_validated from EXIT_STAT
    path predictions
    path refset_dir
    val method_name

    output:
    path 'predictions.db' into predictions_db
    path 'orthologs.db' into sqlite_db

    when:
    file_validated == 0

    """
    /benchmark/map_relations.py --out predictions.db --db orthologs.db $refset_dir/mapping.json.gz $predictions
    """
}

c_go = Channel.create()
c_ec = Channel.create()
c_g_std = Channel.create()
c_g_std_v2 = Channel.create()
c_geneTrees = Channel.create()
c_sp = Channel.create()
c_vg = Channel.create()
c_fas = Channel.create()

process scheduleMetrics {
    
    input:
    val file_validated from EXIT_STAT
    val benchmark from benchmarks_chan
    
    output:
    val v_go into c_go
    val v_ec into c_ec
    val v_std into c_std
    val v_g_std into c_g_std
    val v_g_std_v2 into c_g_std_v2
    val v_geneTrees into c_geneTrees
	val v_sp into c_sp
	val v_vgnc into c_vgnc
	val v_fas into c_fas
    
    when:
    file_validated == 0
    
    // Setting up the cascade of events
    exec:
    
    def m
    v_go = null
    v_ec = null
    v_std = null
    v_g_std = null
    v_g_std_v2 = null
    v_geneTrees = null
    v_sp = null
    v_vgnc = null
    v_fas = null

    switch(benchmark) {
        case "GO":
            v_go = benchmark
            break
        case "EC":
            v_ec = benchmark
            break
        case ~/^STD_(.+)$/:
            m = benchmark =~ /^STD_(.+)$/
            def clade0 = m[0][1]
            if(tree_clades0.contains(clade0)) {
                v_std = clade0
            } else {
                println "WARNING: Unmatched STD benchmark $benchmark"
            }
            break
        case ~/^G_STD_(.+)$/:
            m = benchmark =~ /^G_STD_(.+)$/
            def clade = m[0][1]
            if(tree_clades.contains(clade)) {
                v_g_std = clade
            } else {
                println "WARNING: Unmatched G_STD benchmark $benchmark"
            }
            break
        case ~/^G_STD2_(.+)$/:
            m = benchmark =~ /^G_STD2_(.+)$/
            def clade2 = m[0][1]
            if(tree_clades2.contains(clade2)) {
                v_g_std_v2 = clade2
            } else {
                println "WARNING: Unmatched G_STD2 benchmark $benchmark"
            }
            break
	    case "VGNC":
            v_vgnc = benchmark
            break
        case "SP":
            v_sp = benchmark
            break
        case "FAS":
            v_fas = benchmark
            break
        default:
            if(genetree_sets.contains(benchmark)) {
                v_geneTrees = benchmark
            } else {
                println "WARNING: Unmatched benchmark $benchmark"
            }
            break
    }
}




process go_benchmark {

    label "darwin"

    input:
    tuple val(benchmark), path(db)  from c_go.filter({ it != null }).combine(db_go_test)
    val method_name
    path refset_dir
    val go_evidences
    val community_id
    path result_file_path
    // for mountpoint 
    path predictions
    
    output:
    path "GO.json" into GO_STUB
    
    """
    /benchmark/GoTest.sh -o "${result_file_path}/GO" -a GO.json -c "$community_id" -e "$go_evidences" $db "$method_name" $refset_dir
    """
}

process ec_benchmark {

    label "darwin"

    input:
    tuple val(benchmark), path(db)  from c_ec.filter({ it != null }).combine(db_ec_test)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint 
    path predictions

    output:
    path "EC.json" into EC_STUB
    
    """
    /benchmark/EcTest.sh -o "${result_file_path}/EC" -a EC.json -c "$community_id" $db "$method_name" $refset_dir
    """
}

process swissprot_benchmark {
    label "py"

    input:
    tuple val(benchmark), path(db)  from c_sp.filter({ it != null }).combine(db_sp)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint
    path predictions

    output:
    path "SP.json" into SP_STUB

    """
    /benchmark/swissprot_benchmark.py \
         --com $community_id \
         --participant "$method_name" \
         --assessment-out "SP.json" \
         --outdir "${result_file_path}/SwissProtIDs" \
         --mapping "${refset_dir}/mapping.json.gz" \
         --sp-entries $refset_dir/swissprot.txt.gz \
         --strategy ids_exist_in_both \
         --lineage-tree $refset_dir/lineage_tree.phyloxml \
         --db $db
    """
}


process vgnc_benchmark {
    label "py"

    input:
    tuple val(benchmark), path(sqlite_db) from c_vgnc.filter({it != null }).combine(db_vgnc)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint
    path predictions

    output:
    path "VGNC.json" into VGNC_STUB

    """
    /benchmark/vgnc_benchmark.py \
         --com $community_id \
         --participant "$method_name" \
         --assessment-out "VGNC.json" \
         --outdir "${result_file_path}/VGNC" \
         --vgnc-orthologs $refset_dir/vgnc-orthologs.txt.gz \
         --db $sqlite_db
    """
}


process fas_benchmark{
    label "fas"
    cpus = 4

    input:
    tuple val(benchmark), path(sqlite_db) from c_fas.filter({it != null }).combine(db_fas)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint
    path predictions

    output:
    path "FAS.json" into FAS_STUB

    """
    fas_benchmark.py \
         --com $community_id \
         --participant "$method_name" \
         --assessment-out "FAS.json" \
         --outdir "${result_file_path}/FAS" \
         --fas-precomputed-scores ${refset_dir}/fas_subset.json \
         --fas-data ${refset_dir}/fas_annotations/ \
         --db $sqlite_db
    """
}


process speciestree_benchmark {

    label "darwin"
    tag "$clade"

    input:
    set val(clade), path(db)  from c_std.filter({ it != null }).combine(db_std)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint 
    path predictions

    output:
    path "STD_${clade}.json" into STD_STUB

    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "${result_file_path}/STD_${clade}" -a "STD_${clade}.json" -c "$community_id" -p $clade -m 0 $db "$method_name" $refset_dir
    """
}


process g_speciestree_benchmark {

    label "darwin"
    tag "$clade"

    input:
    set val(clade), path(db)  from c_g_std.filter({ it != null }).combine(db_g_std)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint 
    path predictions

    output:
    path "G_STD_${clade}.json" into G_STD_STUB

    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "${result_file_path}/G_STD_${clade}" -a "G_STD_${clade}.json" -c "$community_id" -p $clade -m 1 $db "$method_name" $refset_dir
    """
}

process g_speciestree_benchmark_variant2 {
    label "darwin"
    tag "$clade"

    input:
    set val(clade), path(db)  from c_g_std_v2.filter({ it != null }).combine(db_g_std_v2)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint 
    path predictions

    output:
    path "G_STD2_${clade}.json" into G_STD2_STUB

    """
    /benchmark/SpeciesTreeDiscordanceTest.sh -o "${result_file_path}/G_STD2_${clade}" -a "G_STD2_${clade}.json" -c "$community_id" -p $clade -m 2 $db "$method_name" $refset_dir
    """
}


process reference_genetrees_benchmark {
    label "darwin"
    tag "$testset"

    input:
    set val(testset), path(db)   from c_geneTrees.filter({ it != null }).combine(db_geneTrees)
    val method_name
    path refset_dir
    val community_id
    path result_file_path
    // for mountpoint 
    path predictions

    output:
    path "${testset}.json" into REFPHYLO_STUB

    """
    /benchmark/RefPhyloTest.sh -o "$result_file_path/${testset}" -a "${testset}.json" -t "$testset" $db "$method_name" $refset_dir
    """
}


challenge_assessments = GO_STUB.mix(EC_STUB, SP_STUB, STD_STUB, G_STD_STUB, G_STD2_STUB, REFPHYLO_STUB, VGNC_STUB, FAS_STUB)

process consolidate {
    label "py"

    input:
    path participants from PARTICIPANT_STUB.collect()
    path challenge_stubs from challenge_assessments.collect()
    path benchmark_data, stageAs: "reference_results_path"
    path assessment_out
    path data_model_export_dir
    path result_file_path
    //for mountpoint
    path predictions

    """
    python /benchmark/manage_assessment_data.py -m $challenge_stubs -b $benchmark_data -o $result_file_path
    python /benchmark/merge_data_model_files.py -p $participants  -m $challenge_stubs -r $result_file_path -a $assessment_out -o $data_model_export_dir
    """
}



workflow.onComplete {
	println ( workflow.success ? "Done!" : "Oops .. something went wrong" )
}
