#!/usr/bin/env python3
import os
import csv
import collections
import argparse
import sqlite3


class ConsensusBuilder:
    def __init__(self):
        self.cons = collections.defaultdict(list)

    def add_method(self, file, name=None):
        if not name:
            base = os.path.basename(file)
            name = base[:base.index('.')]
        with open(file, 'r', newline="") as fh:
            reader = csv.reader(fh, dialect=csv.excel_tab)
            for row in reader:
                if (row[0], row[1]) not in self.cons and (row[1], row[0]) in self.cons:
                    row[0], row[1] = row[1], row[0]
                self.cons[(row[0], row[1])].append(name)

    def dump_consensus(self, out, min_methods=1):
        with open(out, 'w') as fh:
            for (p1, p2), methods in self.cons.items():
                if len(methods) >= min_methods:
                    fh.write("{}\t{}\t{}\t{}\n".format(p1, p2, len(methods), "\t".join(methods)))


class ConsensusBuilderDBs(ConsensusBuilder):

    def add_method(self, db, name=None):
        if not name:
            base = os.path.basename(db)
            name = base[:base.index('.')]
        cons_db = sqlite3.connect(db)
        cur = cons_db.cursor()
        cur.execute("SELECT p1.uniprot_id, p2.uniprot_id FROM orthologs JOIN proteomes as p1 ON orthologs.prot_nr1 = p1.prot_nr JOIN proteomes as p2 ON orthologs.prot_nr2 = p2.prot_nr WHERE p1.uniprot_id < p2.uniprot_id")
        cur.arraysize = 100000
        while True:
            chunk = cur.fetchmany()
            if len(chunk) == 0:
                break
            for pair in chunk:
                self.cons[pair].append(name)
        cons_db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser('build consensus calls')
    parser.add_argument('--out', required=True, help="output filename")
    parser.add_argument('file', nargs='+', help='prediction file')
    parser.add_argument('--sqlite', action="store_true", default=False, help="Flag to indicate that files are sqlite3 databases")
    parser.add_argument('--min-methods', type=int, default=1, help="Number of methods required to include a pairwise prediction into the consensus set.")
    conf = parser.parse_args()
    cons = ConsensusBuilderDBs() if conf.sqlite else ConsensusBuilder()
    for method in conf.file:
        cons.add_method(method)
    cons.dump_consensus(conf.out, conf.min_methods)


