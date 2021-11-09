#!/usr/bin/env python3
import collections
import io
import itertools
import json
import logging
import math
import os
import sqlite3

import Bio.Phylo
import dendropy

from JSON_templates import write_assessment_dataset
from helpers import auto_open, load_json_file

logger = logging.getLogger("HGNC-Benchmark")
Protein = collections.namedtuple("Protein", ["Acc", "Species"])


def compute_hgnc_benchmark(hgnc_orthologs, db_path, raw_out):

    def get_prot_data_for(proteins):
        data = {}
        cur = con.cursor()
        placeholder = ",".join('?' * len(proteins))
        query = f"SELECT * FROM proteomes WHERE prot_nr IN ({placeholder})"
        cur.execute(query, proteins)
        for row in cur.fetchall():
            data[row[0]] = Protein(row[1], row[2])
        return data

    def get_existing_orthologs(all_orthologs):
        def get_chunk(orthologs):
            template = " OR ".join(["(prot_nr1 == ? AND prot_nr2 == ?)"] * len(orthologs))
            query = f"SELECT * FROM orthologs WHERE {template}"
            logger.debug(query)
            args = list(itertools.chain.from_iterable(orthologs))
            cur.execute(query, args)
            return cur.fetchall()

        cur = con.cursor()
        res = []
        for chunk in range(0, len(all_orthologs), 500):
            res.extend(get_chunk(all_orthologs[chunk:chunk+500]))
        return res

    def write_raw_rels(out, rels, typ):
        for en1, en2 in rels:
            out.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(protein_infos[en1].Acc,
                                                        protein_infos[en2].Acc,
                                                        typ,
                                                        hgnc_orthologs[(en1, en2)],
                                                        protein_infos[en1].Species,
                                                        protein_infos[en2].Species))

    con = sqlite3.connect(db_path)
    nr_true = len(hgnc_orthologs)
    missing_true_orthologs = set(hgnc_orthologs.keys())
    logger.info(f"HGNC asserts {nr_true} orthologous relations")
    hgnc_genes = list(set(itertools.chain.from_iterable(hgnc_orthologs.keys())))
    protein_infos = get_prot_data_for(hgnc_genes)

    all_predicted_orthologs_among_hgnc_genes = get_existing_orthologs(list(hgnc_orthologs.keys()))
    logger.info(f"Method predicted {len(all_predicted_orthologs_among_hgnc_genes)} among the set of "
                f"{len(hgnc_genes)} genes in the HGNC dataset")
    missing_true_orthologs -= set((x[0], x[1]) for x in all_predicted_orthologs_among_hgnc_genes)
    logger.info(f"Method didn't predict {len(missing_true_orthologs)} asserted orthologs")
    true_positives = set(hgnc_orthologs.keys()) - missing_true_orthologs
    tp = len(hgnc_orthologs) - len(missing_true_orthologs)

    write_raw_rels(raw_out, true_positives, "TP")
    write_raw_rels(raw_out, missing_true_orthologs, "FN")
    tpr = tp / nr_true
    logger.info("TPR: {}; nr_true: {}".format(tpr, nr_true))
    metrics = [{"name": "TP", 'value': tp},
               {"name": "FN", "value": len(missing_true_orthologs)},
               {"name": "TPR", "value": tpr, "stderr": 1.96 * math.sqrt(tpr * (1 - tpr) / nr_true)},
              ]
    return metrics


def get_hgnc_orthologs(hgnc_orthologs):
    orthologs = {}
    with auto_open(hgnc_orthologs, 'rt') as fh:
        for line in fh:
            a, b, fam = line.strip().split("\t")
            a = int(a)
            b = int(b)
            orthologs[(min(a,b), max(a,b))] = fam
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
    parser.add_argument('--hgnc-orthologs', required=True, help="Path to textfile with HGNC asserted orthologs")
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
