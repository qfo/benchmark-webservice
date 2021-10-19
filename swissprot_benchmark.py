#!/usr/bin/env python3
import json
import logging
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

    def get_swissprot_orthologs_of(prot_nr):
        cur = con.cursor()
        cur.execute("SELECT DISTINCT prot_nr2 FROM orthologs WHERE prot_nr1 == ? AND prot_nr1 < prot_nr2 ORDER BY prot_nr2", (prot_nr, ))
        return [z[0] for z in cur.fetchall() if z[0] in sp_entries]

    def are_same_sp_id(enrs):
        sp_ids = [sp_entries[enr].split('_')[0] for enr in enrs]
        return all(sp_ids[0] == sp_id for sp_id in sp_ids)

    con = sqlite3.connect(db_path)
    orthologs_among_sp = 0
    conserved_sp_id = 0
    for sp_entry in sp_entries:
        orths = get_swissprot_orthologs_of(sp_entry)
        orthologs_among_sp += len(orths)
        conserved_sp_id += sum(map(lambda en: are_same_sp_id((sp_entry, en)), orths))
    return conserved_sp_id, orthologs_among_sp


def write_assessment_json_stub(fn, community, participant, result):
    challenge = "SwissProtIDs"
    stubs = []
    for metric in result:
        id_ = "{}:{}_{}_{}_A".format(community, challenge, metric['name'], participant.replace(' ', '-').replace('_', '-'))
        stubs.append(write_assessment_dataset(id_, community, challenge, participant, metric['name'], metric['value'], metric.get('stderr', 0)))
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
    conserved_sp_ids, orthologs_among_sp = compute_sp_benchmark(sp_entries, conf.db)
    res = [{'name': 'Nr conserved SwissProtIDs', 'value': conserved_sp_ids},
           {'name': 'Nr orthologs among SwissProt entries', 'value': orthologs_among_sp}]
    write_assessment_json_stub(conf.out, conf.com, conf.participant, res)



