#!/usr/bin/env python3
import itertools
import json
import logging
import math
import sqlite3

from JSON_templates import write_assessment_dataset
from helpers import auto_open, load_json_file

logger = logging.getLogger("SP-Benchmark")


def get_swissprot_entries(mapping_path, sp_file):
    mapping = load_json_file(mapping_path)
    sp_entries = {}
    excluded = 0
    with auto_open(sp_file, 'rt') as fh:
        for line in fh:
            # line contains >sp|A0A0R4IKJ1|CAPAM_DANRE
            sp = line.strip().split('|')[-1]
            try:
                enr = mapping['mapping'][sp]
                sp_entries[enr] = sp
            except KeyError:
                if 'excluded_ids' not in mapping or sp not in mapping['excluded_ids']:
                    raise
                excluded += 1
    logger.info("{} swissprot IDs from excluded species ignored".format(excluded))
    logger.info("found {} swissprot entries".format(len(sp_entries)))
    return sp_entries


def compute_sp_benchmark(sp_entries, db_path):
    def get_true_orthologs_by_identical_ids():
        res = set([])

        def sorter_sp_id(x):
            return x[0].rsplit('_', 1)[0]

        sorted_sp_entries = sorted(((v, k) for k, v in sp_entries.items()), key=sorter_sp_id)
        for grp, entries in itertools.groupby(sorted_sp_entries, key=sorter_sp_id):
            res.update({(min(x[1], y[1]), max(x[1],y[1])) for x, y in itertools.combinations(entries, 2)})
        return res

    def get_swissprot_orthologs_of(prot_nr):
        cur = con.cursor()
        cur.execute(
            "SELECT DISTINCT prot_nr2 FROM orthologs WHERE prot_nr1 == ? AND prot_nr1 < prot_nr2 ORDER BY prot_nr2",
            (prot_nr,))
        return [z[0] for z in cur.fetchall() if z[0] in sp_entries]

    def are_same_sp_id(*enrs):
        sp_ids = [sp_entries[enr].rsplit('_', 1)[0] for enr in enrs]
        return all(sp_ids[0] == sp_id for sp_id in sp_ids)

    def are_prefix_or_same_id(x, y):
        sp_ids = [sp_entries[enr].rsplit('_', 1)[0] for enr in (x, y)]
        sp_ids.sort(key=lambda x: len(x))
        return all(sp_ids[0] == sp_id or sp_id.startswith(sp_ids[0]) for sp_id in sp_ids)

    def no_common_prefix(x, y):
        return sp_entries[x][0] != sp_entries[y][0]

    con = sqlite3.connect(db_path)
    orthologs_among_sp = 0
    conserved_sp_id = 0
    all_trues = frozenset(get_true_orthologs_by_identical_ids())
    missing_true_orthologs = set(all_trues)
    nr_true = len(all_trues)
    fp = 0
    for sp_entry in sp_entries:
        orths = get_swissprot_orthologs_of(sp_entry)
        orthologs_among_sp += len(orths)
        fp += sum((no_common_prefix(sp_entry, en) for en in orths))
        fnd_good = {(sp_entry, en) for en in orths if are_same_sp_id(sp_entry, en)}
        if len(fnd_good - all_trues) > 0:
            missing = fnd_good - all_trues
            logger.error("{} missing for {}:".format(len(missing), sp_entry))
            for x, y in missing:
                logger.error("  {} - {} missing in true set".format(sp_entries[x], sp_entries[y]))
            raise Exception("all_trues set seems incomplete")
        conserved_sp_id += len(fnd_good)
        missing_true_orthologs.difference_update(fnd_good)

    tpr = conserved_sp_id / nr_true
    ppv = conserved_sp_id / (fp + conserved_sp_id)
    logger.info("TPR: {}; PPV: {}, nr_true: {}".format(tpr, ppv, nr_true))
    metrics = [{"name": "TP", 'value': conserved_sp_id},
               {"name": "Nr orthologs among SwissProt entries", 'value': orthologs_among_sp},
               {"name": "FP", "value": fp},
               {"name": "FN", "value": len(missing_true_orthologs)},
               {"name": "TPR", "value": tpr, "stderr": 1.96 * math.sqrt(tpr * (1 - tpr) / nr_true)},
               {"name": "PPV", "value": ppv, "stderr": 1.96 * math.sqrt(ppv * (1 - ppv) / (fp + conserved_sp_id))},
               ]
    return metrics


def write_assessment_json_stub(fn, community, participant, result):
    challenge = "SwissProtIDs"
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

    parser = argparse.ArgumentParser(description="SwissProtID conservation benchmark")
    parser.add_argument('--mapping', required=True, help="Path to mapping.json of proper QfO dataset")
    parser.add_argument('--out', required=True, help="Path to output file")
    parser.add_argument('--db', required=True, help="Path to sqlite database with pairwise predictions")
    parser.add_argument('--com', required=True, help="community id")
    parser.add_argument('--sp-entries', required=True, help="Path to textfile with SwissProt IDs")
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

    sp_entries = get_swissprot_entries(conf.mapping, conf.sp_entries)
    res = compute_sp_benchmark(sp_entries, conf.db)
    write_assessment_json_stub(conf.out, conf.com, conf.participant, res)
