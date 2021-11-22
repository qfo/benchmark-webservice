#!/usr/bin/env python3
import collections
import itertools
import json
import logging
import math
import os
import sqlite3

from JSON_templates import write_assessment_dataset
from helpers import auto_open

logger = logging.getLogger("HGNC-Benchmark")
Protein = collections.namedtuple("Protein", ["Acc", "Species", "HGNC_ID"])


def compute_hgnc_benchmark(hgnc_orthologs, db_path, raw_out):
    def get_prot_data_for(proteins):
        hgnc_fam = {}
        for (p1, p2), fam in hgnc_orthologs.items():
            hgnc_fam[p1] = fam
            hgnc_fam[p2] = fam

        cur = con.cursor()
        placeholder = ",".join('?' * len(proteins))
        query = f"SELECT * FROM proteomes WHERE prot_nr IN ({placeholder})"
        cur.execute(query, proteins)

        data = {}
        for row in cur.fetchall():
            data[row[0]] = Protein(row[1], row[2], hgnc_fam[row[0]])
        return data

    def get_orthologs_among_subset_of_proteins(proteins):
        query = f"SELECT * FROM orthologs WHERE prot_nr1 == ? AND prot_nr1 < prot_nr2"
        prot_set = set(proteins)

        def get_orthologs_for_query(query_protein):
            cur = con.cursor()
            cur.execute(query, (query_protein,))
            return [rel for rel in cur.fetchall() if rel[1] in prot_set]

        for p in prot_set:
            yield from get_orthologs_for_query(p)

    def write_raw_rels(out, rels, typ):
        for en1, en2 in rels:
            out.write(
                f"{protein_infos[en1].Acc}\t{protein_infos[en2].Acc}\t{typ}\t"
                f"{protein_infos[en1].HGNC_ID}\t{protein_infos[en2].HGNC_ID}\t"
                f"{protein_infos[en1].Species}\t{protein_infos[en2].Species}\n")

    con = sqlite3.connect(db_path)
    nr_true = len(hgnc_orthologs)
    missing_true_orthologs = set(hgnc_orthologs.keys())
    logger.info(f"HGNC asserts {nr_true} orthologous relations")
    hgnc_genes = list(set(itertools.chain.from_iterable(hgnc_orthologs.keys())))
    protein_infos = get_prot_data_for(hgnc_genes)

    all_predicted_orthologs_among_hgnc_genes = set(get_orthologs_among_subset_of_proteins(hgnc_genes))
    logger.info(f"Method predicted {len(all_predicted_orthologs_among_hgnc_genes)} among the set of "
                f"{len(hgnc_genes)} genes in the HGNC dataset")
    missing_true_orthologs -= set((x[0], x[1]) for x in all_predicted_orthologs_among_hgnc_genes)
    logger.info(f"Method didn't predict {len(missing_true_orthologs)} asserted orthologs")
    true_positives = set(hgnc_orthologs.keys()) - missing_true_orthologs
    tp = len(hgnc_orthologs) - len(missing_true_orthologs)
    tpr = tp / nr_true

    hgnc_per_species = collections.defaultdict(set)
    for info in protein_infos.values():
        hgnc_per_species[info.Species].add(info.HGNC_ID)

    false_positives = []
    for p1, p2 in all_predicted_orthologs_among_hgnc_genes:
        if protein_infos[p1].HGNC_ID != protein_infos[p2].HGNC_ID:
            id1_in_sp2 = protein_infos[p1].HGNC_ID in hgnc_per_species[protein_infos[p2].Species]
            id2_in_sp1 = protein_infos[p2].HGNC_ID in hgnc_per_species[protein_infos[p1].Species]
            is_fp = id1_in_sp2 and id2_in_sp1
            logger.debug(
                f"is used as fp: {is_fp:1} -- "
                f"{protein_infos[p1].HGNC_ID} ({protein_infos[p1].Acc}) vs {protein_infos[p2].HGNC_ID} ({protein_infos[p2].Acc}): "
                f"{protein_infos[p1].HGNC_ID} in {protein_infos[p2].Species}: {id1_in_sp2}; "
                f"{protein_infos[p2].HGNC_ID} in {protein_infos[p1].Species}: {id2_in_sp1}")

            if is_fp:
                false_positives.append((p1, p2))

    nr_pos = tp + len(false_positives)
    ppv = tp / nr_pos

    write_raw_rels(raw_out, true_positives, "TP")
    write_raw_rels(raw_out, false_positives, "FP")
    write_raw_rels(raw_out, missing_true_orthologs, "FN")
    logger.info(f"TPR: {tpr}; nr_true: {nr_true}")
    logger.info(f"PPV: {ppv}; nr_pos: {nr_pos}")

    metrics = [{"name": "TP", 'value': tp},
               {"name": "FN", "value": len(missing_true_orthologs)},
               {"name": "TPR", "value": tpr, "stderr": 1.96 * math.sqrt(tpr * (1 - tpr) / nr_true)},
               {"name": "PPV", "value": ppv, "stderr": 1.96 * math.sqrt(ppv * (1 - ppv) / nr_pos)},
               ]
    return metrics


def get_hgnc_orthologs(hgnc_orthologs_fname):
    orthologs = {}
    with auto_open(hgnc_orthologs_fname, 'rt') as fh:
        for line in fh:
            a, b, fam = line.strip().split("\t")
            a = int(a)
            b = int(b)
            orthologs[(min(a, b), max(a, b))] = fam
    return orthologs


def write_assessment_json_stub(fn, community, participant, result):
    challenge = "HGNC"
    stubs = []
    for metric in result:
        id_ = "{}:{}_{}_{}_A".format(community, challenge, metric['name'],
                                     participant.replace(' ', '-').replace('_', '-'))
        stubs.append(write_assessment_dataset(id_, community, challenge, participant, metric['name'], metric['value'],
                                              metric.get('stderr', 0)))
    with auto_open(fn, 'wt') as fout:
        json.dump(stubs, fout, sort_keys=True, indent=4, separators=(',', ': '))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="HGNC asserted orthologs benchmark")
    parser.add_argument('--assessment-out', required=True, help="Path where assessment json file will be stored")
    parser.add_argument('--outdir', required=True, help="Folder to store the raw output file in")
    parser.add_argument('--db', required=True, help="Path to sqlite database with pairwise predictions")
    parser.add_argument('--com', required=True, help="community id")
    parser.add_argument('--hgnc-orthologs', required=True, help="Path to text file with HGNC asserted orthologs")
    parser.add_argument('--participant', required=True, help="Name of participant method")
    parser.add_argument('--log', help="Path to log file. Defaults to stderr")
    parser.add_argument('-d', '--debug', action="store_true", help="Set logging to debug level")
    conf = parser.parse_args()

    log_conf = {'level': logging.INFO, 'format': "%(asctime)-15s %(levelname)-7s: %(message)s"}
    if conf.log is not None:
        log_conf['filename'] = conf.log
    if conf.debug:
        log_conf['level'] = logging.DEBUG
    logging.basicConfig(**log_conf)
    logger.info("running hgnc_benchmark with following arguments: {}".format(conf))

    os.makedirs(conf.outdir, exist_ok=True)
    outfn_path = os.path.join(conf.outdir,
                              "HGNC_{}_raw.txt.gz".format(conf.participant.replace(' ', '-').replace('_', '-'))
                              )
    hgnc_orthologs = get_hgnc_orthologs(conf.hgnc_orthologs)

    with auto_open(outfn_path, 'wt') as raw_out_fh:
        res = compute_hgnc_benchmark(hgnc_orthologs, conf.db, raw_out_fh)
    write_assessment_json_stub(conf.assessment_out, conf.com, conf.participant, res)
