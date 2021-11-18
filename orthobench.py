#!/usr/bin/env python3

"""
This script calculates the benchmarks for an input set of orthogroups

Instructions:
1. Predict the complete set of orthogroups for the genes in the "Input/" directory
2. Write Orthogroups to a file, one orthogroup per line (header lines and commented
   out lines starting with '#' are allowed). 
3. Download this script and the accompanying RefOGs directory
3. Call the script with the the orthogroup filename as the only argument

By default the script with use regular expressions to extract the genes from the 
additional text on each line. 

You can also specify the option '-b' to use the more basic file reader which requires 
the following format:
- First line is a header and is ignored. 
- One orthogroup per line
- Genes can be separated by commas, spaces or tabs. 
- Lines starting with '#' are comments and are ignored
- Optionally, each line can start with the name of the orthogroup followed by a colon.
   E.g. "OG0000001: Gene1, Gene2"
"""
import math
import os
import re
import sys
import glob
import json
import os
import logging
import tarfile
from argparse import ArgumentParser

from JSON_templates import write_assessment_dataset
from helpers import auto_open

delims = " |,|\t"
logger = logging.getLogger("orthobench")


def read_orthogroups(fn, exp_genes):
    """
    Read the orthogroups from a file formatted as specified above
    """
    ogs = []
    with auto_open(fn, 'rt') as infile:
        for l in infile:
            if l.startswith("#"):
                continue
            t = l.strip()
            genes = re.split(delims, t)
            # remove white spaces
            genes = [g.strip() for g in genes]
            genes = set([g for g in genes if g != ""])
            # intersecting with the set of genes in orthobench
            genes &= exp_genes
            if len(genes - exp_genes) > 0:
                logger.warning(f"group '{l}' contains unknown proteins: {genes - exp_genes}")
            if len(genes) > 1:
                ogs.append(genes)
    return ogs


def check_orthogroups(ogs, exp_genes):
    all_pred_genes = set([g for og in ogs for g in og])
    x = all_pred_genes.difference(exp_genes)
    if len(x) != 0:
        logger.error("found extra genes in input file, check its formatting is correct and there are no incorrect genes")
        print("Examples:")
        for g in list(x)[:10]:
            print(g)
    x = exp_genes.difference(all_pred_genes)
    if len(x) != 0:
        logger.info("Examples of genes not in predictions:")
        for g in list(x)[:3]:
            print(g)

    n_genes = sum([len(og) for og in ogs])
    if n_genes < 0.5 * len(exp_genes):
        logger.error("ERROR: Too many missing genes in predicted orthogroups.")
        logger.error("Orthogroups should contain at least 50% of all genes but")
        logger.error(f"orthogroups file only contained {n_genes} genes ({100*n_genes/len(exp_genes)}%%")
        raise Exception("Too small coverage. Seems you didn't run the full dataset")
    all_genes = [g for og in ogs for g in og]
    n_genes_no_dups = len(set(all_genes))
    if n_genes_no_dups != n_genes:
        logger.error("Some genes appear in multiple orthogroups, benchmark are meaningless with such data.")
        logger.error((n_genes_no_dups, n_genes))
        from collections import Counter
        c = Counter(all_genes)
        for g, n in c.most_common(10):
            logger.error(f"  {n}: {g}")
        raise Exception("Duplicated proteins in groups")
    # checked genes from each of the expected species are present
    p = 100.*n_genes / len(exp_genes)
    logger.info("%d genes found in predicted orthogroups, this is %0.1f%% of all genes" % (n_genes, p))


def read_refogs_from_tarball(tarball, uncertain=False, nr_groups=None):
    refogs = []
    re_og_uncertain_files = re.compile(r"RefOGs\/low_certainty_assignments\/RefOG(?P<nr>\d{3}).txt")
    re_og_files = re.compile(r"RefOGs\/RefOG(?P<nr>\d{3}).txt")

    nr_files = 0
    with tarfile.open(tarball, "r:*") as tar:
        rng = sum(1 for member in tar if re_og_files.match(member.name))
        logger.debug(f"found {rng} RefOGs in dataset")
        refogs = [set([]) for _ in range(rng)]
        re_og = re_og_uncertain_files if uncertain else re_og_files
        for member in tar:
            m = re_og.match(member.name)
            if m:
                nr_files += 1
                with tar.extractfile(member) as infile:
                    og_pos = int(m.group('nr')) - 1
                    refogs[og_pos] = set([g.rstrip().decode() for g in infile.readlines()])
    n = sum([len(r) for r in refogs])
    logger.info(f"extracted {n} proteins from {nr_files} RefOGs (uncertain == {uncertain})")
    expected = {'files': 70, 'genes': 1945}
    if not uncertain and (n != expected['genes'] or nr_files != expected['files']):
        logger.error(f"There are genes missing from the RefOG files. Found {n} genes, expected {expected['genes']} "
                     f"from {nr_files} files, expected {expected['files']}")
        raise Exception("missing genes/files from RefOG data")
    return refogs


def calculate_benchmarks_pairwise(ref_ogs, uncert_genes, pred_ogs, q_even=True, q_remove_uncertain=True, log=None):
    referenceOGs = ref_ogs
    predictedOGs = pred_ogs
    totalFP = 0.
    totalFN = 0.
    totalTP = 0.
    totalGroundTruth = 0.
    n_exact = 0
    n_splits = []
    if log is not None:
        log.write("RefOG\tPredicted OGs\tMissing proteins\tTrue positives\tFalse positives\tFalse negatives\n")

    # so as not to count uncertain genes either way remove them from the 
    # expected and remove them from any predicted OG (as though they never existed!)
    for refOg, uncert in zip(referenceOGs, uncert_genes):
        thisFP = 0.
        thisFN = 0.
        thisTP = 0.
        this_split = 0
        if q_remove_uncertain:
            refOg = refOg.difference(uncert)
        nRefOG = len(refOg)
        log_buffer = {'refOG': "[" + ",".join(refOg) +"]"}

        not_present = set(refOg)
        for predOg in predictedOGs:
            overlap = len(refOg.intersection(predOg))
            if overlap > 0:
                if q_remove_uncertain:
                    predOg = predOg.difference(uncert)   # I.e. only discount genes that are uncertain w.r.t. this RefOG
                overlap = len(refOg.intersection(predOg))
            if overlap > 0:
                this_split += 1
                not_present = not_present.difference(predOg)
                thisTP += overlap * (overlap - 1)/2    # n-Ch-2
                thisFP += overlap * (len(predOg) - overlap)
                thisFN += (nRefOG - overlap) * overlap
                if "ogs" not in log_buffer:
                    log_buffer['ogs'] = []
                log_buffer['ogs'].append("[" + ",".join(predOg) + "]")
        # Are FNs more from splintered OGs or missing genes?
        # print("%f\t%f" % (thisFN/2./(nRefOG-1), len(not_present)*(nRefOG-1)/2./(nRefOG-1))) 
        # finally, count all the FN pairs from those not in any predicted OG
        thisFN += len(not_present)*(nRefOG-1)
        # don't count 'orphan genes' as splits, it's more informative only to count 
        # clusters that this orthogroup has been split into. Recall already counts
        #  the missing genes, this should give a distinct measure.
        # this_split += len(not_present)     
        # All FN have been counted twice
        assert(thisFN % 2 == 0)
        n_splits.append(this_split)
        # print(this_split)      # Orthogroup fragments
        # print(len(not_present))  # Unclustered genes 
        thisFN /= 2 
        # sanity check
        nPairs1 = thisTP + thisFN
        nPairs2 = nRefOG * (nRefOG - 1) / 2
        if nPairs1 != nPairs2:
            logger.error("Pairs do not match! %d != %d" % (nPairs1, nPairs2))
            # print(refOg)
            # print(predOg)
            # print((nRefOG, thisTP, thisFP, thisFN))
            # print("ERROR: Sanity check failed")
#            assert(nPairs1 == nPairs2)
            raise Exception
        totalGroundTruth += nPairs1
        if log is not None:
            missing = "[" + ",".join(not_present) + "]"
            log.write(f"{log_buffer['refOG']}\t{','.join(log_buffer['ogs'])}"
                      f"\t{missing}\t{thisTP}\t{thisFP}\t{thisFN}\n")

        if thisFN == 0 and thisFP == 0:
            n_exact += 1
        if q_even:
            N = float(len(refOg)-1)
            totalFN += thisFN/N
            totalFP += thisFP/N
            totalTP += thisTP/N
        else:
            totalFN += thisFN
            totalFP += thisFP
            totalTP += thisTP
        # print("%d\t%d\t%d" % (thisTP, thisFN, thisFP))  
    TP, FP, FN = (totalTP, totalFP, totalFN)
    # print("%d Correct gene pairs" % TP)
    # print("%d False Positives gene pairs" % FP)
    # print("%d False Negatives gene pairs\n" % FN)
    pres = TP/(TP+FP)
    recall = TP/(TP+FN)
    f = 2*pres*recall/(pres+recall)
    print("%0.1f%% F-score" % (100.*f))
    print("%0.1f%% Precision" % (100.*pres))
    print("%0.1f%% Recall\n" % (100.*recall))
    print("%d Orthogroups exactly correct" % n_exact)
    metrics = [{"name": "TP", 'value': TP},
               {"name": "FN", "value": FN},
               {"name": "FP", "value": FP},
               {"name": "TPR", "value": recall, "stderr": 1.96 * math.sqrt(recall * (1 - recall) / (TP + FN))},
               {"name": "PPV", "value": pres, "stderr": 1.96 * math.sqrt(pres * (1 - pres) / (TP + FN))},
               {"name": "F-score", "value": f},
               ]
    return metrics

    
def benchmark(ogs_filename, refogs_tarball, ob_2_qfo, rawlog=None):
    logger.info("Reading RefOGs from: %s" % refogs_tarball)

    def filter_groups(grps):
        return [set((ob_2_qfo[x] for x in group if x in ob_2_qfo)) for group in grps]

    ref_ogs = filter_groups(read_refogs_from_tarball(refogs_tarball, uncertain=False))
    ref_ogs_uncertain = filter_groups(read_refogs_from_tarball(refogs_tarball, uncertain=True))
    logger.info(f"Filtered (QfO) groups contain {len(ref_ogs)} groups with {sum(len(z) for z in ref_ogs)} proteins")
    logger.info(f"Filtered (QfO) uncertain groups contain {len(ref_ogs_uncertain)} groups "
                f"with {sum(len(z) for z in ref_ogs_uncertain)} proteins")

    exp_genes = set(ob_2_qfo.values())
    logger.info("Reading predicted orthogroups from: %s" % ogs_filename)

    pred_ogs = read_orthogroups(ogs_filename, exp_genes)

    check_orthogroups(pred_ogs, exp_genes)
    logger.info("Calculating benchmarks:")
    return calculate_benchmarks_pairwise(ref_ogs, ref_ogs_uncertain, pred_ogs, log=rawlog)


def write_assessment_json_stub(fn, config, result):
    challenge = config.challenge_id
    stubs = []
    for metric in result:
        id_ = "{}:{}_{}_{}_A".format(config.community_id, challenge, metric['name'],
                                     config.participant_id.replace(' ', '-').replace('_', '-'))
        stubs.append(write_assessment_dataset(id_, config.community_id, challenge, config.participant_id,
                                              metric['name'], metric['value'], metric.get('stderr', 0)))
    with auto_open(fn, 'wt') as fout:
        json.dump(stubs, fout, sort_keys=True, indent=4, separators=(',', ': '))



def make_assessment_stub(metric, metric_value, metric_error, config):
    id_ = "{}:{}_{}_{}_A".format(config.community_id, config.challenge_id, metric, config.participant_id)
    data = {
        "_id": id_,
        "community_id": config.community_id,
        "challenge_id": config.challenge_id,
        "participant_id": config.participant_id,
        "type": "assessment",
        "metrics": {
            "metric_id": metric,
            "value": metric_value,
            "stderr": metric_error,
        }
    }
    return data


def load_mapping_from_orthobench_2_qfo(orthobench_to_qfo):
    with auto_open(orthobench_to_qfo, 'rt', encoding="utf-8") as fh:
        mapping = {}
        for line in fh:
            ob, qfo = line.strip().split('\t')
            mapping[ob] = qfo
    return mapping


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-p", "--participant-id", required=True,
                        help="name of the tool/participant")
    parser.add_argument("-c", "--community-id", required=True,
                        help="community_id, Name or OEB permanent ID for the benchmarking community")
    parser.add_argument("-b", "--challenge-id", required=True, help="id/name of the benchmark")
    parser.add_argument("-r", "--reference-groups", required=True,
                        help="tarfile containing the reference groups files")
    parser.add_argument("--orthobench-to-qfo", required=True,
                        help="mapping file from orthobench protein identifiers to QfO uniprot identifiers")
    parser.add_argument("-g", "--predicted-groups", required=True,
                        help="file containing the predicted groups in flat format (one group per line)")
    parser.add_argument("-a", "--assessment-out", required=True,
                        help="file where the json assessment file should be written")
    parser.add_argument("-o", "--outdir", required=True,
                        help="output dir containing the detailed raw benchmark results")
    parser.add_argument('--log', help="Path to log file. Defaults to stderr")
    parser.add_argument('-d', '--debug', action="store_true", help="Set logging to debug level")
    conf = parser.parse_args()

    log_conf = {'level': logging.INFO, 'format': "%(asctime)-15s %(levelname)-7s: %(message)s"}
    if conf.log is not None:
        log_conf['filename'] = conf.log
    if conf.debug:
        log_conf['level'] = logging.DEBUG
    logging.basicConfig(**log_conf)

    # load mapping betweeen orthobench and qfo ids
    ob_to_qfo = load_mapping_from_orthobench_2_qfo(conf.orthobench_to_qfo)
    outfn = os.path.join(conf.outdir,
                         "{}_{}_raw.txt.gz".format(conf.challenge_id,
                                                   conf.participant_id.replace(' ', '-').replace('_', '-'))
                         )
    os.makedirs(conf.outdir, exist_ok=True)
    with auto_open(outfn, 'wt') as rawlog:
        # reference data (reference groups as defined) can be loaded from conf.reference_groups
        results = benchmark(conf.predicted_groups, conf.reference_groups, ob_to_qfo, rawlog=rawlog)

    write_assessment_json_stub(conf.assessment_out, conf, results)

