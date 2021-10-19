#!/usr/bin/env python3
import collections
import csv
import json
import math
import sys
from bisect import bisect_right
from time import time
try:
    import lxml.etree as etree
except ImportError:
    import xml.etree.ElementTree as etree
import re
import itertools
import sqlite3
import logging
from helpers import auto_open, unique, load_json_file
logger = logging.getLogger("relations-processor")


# uniprot accession regex: https://www.uniprot.org/help/accession_numbers
RE_UP = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$")


def encode_nr_as_seq(nr):
    AA = 'ARNDCQEGHILKMFPSTWYVX$'
    base = 16
    N = math.floor(math.log(nr, base)+1)
    res = ['X']
    rem = nr
    for i in range(N):
        x = math.floor(rem / base)
        res.append(AA[rem - base * x])
        rem = x
    res.append('X')
    return "".join(res)


def load_mapping(path):
    return load_json_file(path)


class PairwiseOrthologRelationExtractor(object):
    def __init__(self, mapping_data, dbi):
        self.valid_id_map = mapping_data['mapping']
        self.internal_genome_offs = mapping_data['Goff']
        self.species_order = mapping_data['species']
        self.excluded_ids = mapping_data['excluded_ids'] if 'excluded_ids' in mapping_data else set([])
        self.dbi = dbi
        self.genome_cnt = 0
        self.generef_to_internal_id = {}
        self.internal_to_genome_nr = {}
        self.processed_stats = {'last': time(), 'processed_toplevel': 0, 'relations': 0}

    def add_genome_genes(self, genome_node):
        self.genome_cnt += 1
        internal_ids = []
        for gene in genome_node.findall('.//{http://orthoXML.org/2011/}gene'):
            gene_id = gene.get('id')
            gene_prot_id = gene.get('protId')
            try:
                internal_id = self.valid_id_map[gene_prot_id]
                self.generef_to_internal_id[int(gene_id)] = internal_id
                self.internal_to_genome_nr[internal_id] = self.genome_cnt
                internal_ids.append(internal_id)
            except KeyError:
                if gene_prot_id not in self.excluded_ids:
                    logger.warning("protId {} of gene(id={}) (in species {}) is not known in this dataset"
                                   .format(gene_prot_id, gene_id, genome_node.get('name')))
        if len(internal_ids) == 0:
            logger.info("Genome {} does not contain any mapped genes".format(genome_node.get('name')))
            return True
        min_id = min(internal_ids) - 1
        max_id = max(internal_ids) - 1
        k_min = bisect_right(self.internal_genome_offs, min_id)
        k_max = bisect_right(self.internal_genome_offs, max_id)
        if k_min != k_max:
            cnts = collections.Counter(
                (self.species_order[bisect_right(self.internal_genome_offs, int_id-1) - 1]
                for int_id in internal_ids)).most_common()
            logger.error("Not all crossreferences used in species '{}' map to the same species: {}"
                         .format(genome_node.get('name'), cnts))
            return False
        return True

    def check_unique_id_mapping(self):
        mapping_ok = True
        c = collections.Counter(self.generef_to_internal_id.values())
        for internal_id, cnts in filter(lambda x: x[1]>1, c.most_common()):
            gene_refs = list(filter(lambda x: x[1]==internal_id, self.generef_to_internal_id.items()))
            logger.error("{} different geneRefs {} map to the same reference protein"
                         .format(cnts, gene_refs))
            mapping_ok = False
        return mapping_ok

    def log_progress(self):
        logger.info("processed {} toplevel orthologGroups with {} induced pairwise relations"
                    .format(self.processed_stats['processed_toplevel'],
                            self.processed_stats['relations']))

    def extract_pairwise_relations(self, node):
        nr_rels = 0

        def _rec_extract(node):
            nonlocal nr_rels
            if node.tag == "{http://orthoXML.org/2011/}geneRef":
                try:
                    return {self.generef_to_internal_id[int(node.get('id'))]}
                except KeyError:
                    logger.info("skipping relations involving gene(id={})".format(node.get('id')))
                    return set([])
            elif node.tag in ('{http://orthoXML.org/2011/}orthologGroup', '{http://orthoXML.org/2011/}paralogGroup'):
                nodes_of_children = [_rec_extract(child) for child in node]
                if node.tag == '{http://orthoXML.org/2011/}orthologGroup':
                    for child1, child2 in itertools.combinations(nodes_of_children, 2):
                        for gId1, gId2 in itertools.product(child1, child2):
                            if self.internal_to_genome_nr[gId1] != self.internal_to_genome_nr[gId2]:
                                self.dbi.add_orthologs(gId1, gId2)
                                nr_rels += 1
                nodes = set.union(*nodes_of_children)
                return nodes
            else:
                return set([])

        nodes = _rec_extract(node)
        logger.debug("extracting {} pairwise orthologous relations from toplevel group {} with {} valid genes"
                     .format(nr_rels, node.get('id', 'n/a'), len(nodes)))
        self.processed_stats['processed_toplevel'] += 1
        self.processed_stats['relations'] += nr_rels
        if time() - self.processed_stats['last'] > 20:
            self.log_progress()
            self.processed_stats['last'] = time()


def parse_orthoxml(fh, processor):
    nsmap = {}
    og_level = 0

    def fixtag(ns, tag):
        return "{" + nsmap[ns] + "}" + tag

    logger.info("start mapping of orthoxml formatted input file")
    for event, elem in etree.iterparse(fh, events=('start-ns', 'start', 'end')):
        if event == 'start-ns':
            ns, url = elem
            nsmap[ns] = url
        elif event == 'start' and elem.tag == fixtag('', 'orthologGroup'):
            og_level += 1
        elif event == 'start' and elem.tag == fixtag('', 'groups'):
            if not processor.check_unique_id_mapping():
                sys.exit(2)
        if event == 'end':
            if elem.tag == fixtag('', 'orthologGroup'):
                og_level -= 1
                if og_level == 0:
                    processor.extract_pairwise_relations(elem)
                    elem.clear()
            elif elem.tag == fixtag('', 'species'):
                if not processor.add_genome_genes(elem):
                    sys.exit(2)
                elem.clear()
    processor.log_progress()


def parse_tsv(fh, mapping_data):
    logger.info("start mapping of tsv formatted input data")
    valid_id_map = mapping_data['mapping']
    excluded_ids = mapping_data['excluded_ids'] if 'excluded_ids' in mapping_data else set([])
    goff = mapping_data['Goff']
    dialect = csv.Sniffer().sniff(fh.read(2048))
    fh.seek(0)
    csv_reader = csv.reader(fh, dialect)
    for line_nr, row in enumerate(csv_reader):
        if len(row) < 2:
            logger.warning("skipping relation on line {} ({})"
                           .format(line_nr, row))
            continue
        try:
            id1, id2 = (valid_id_map[z] for z in row[:2])
            if bisect_right(goff, id1 - 1) == bisect_right(goff, id2 - 1):
                logger.warning("skipping dubious orthology relation {} within same gnome"
                               .format(row))
                continue
            yield id1, id2
        except KeyError:
            unkn = list(itertools.filterfalse(lambda x: x in valid_id_map, row[:2]))
            unkn = list(itertools.filterfalse(lambda x: x in excluded_ids, unkn))
            if len(unkn)>0:
                logger.warning("relation {} contains unknown ID: {}".format(row, unkn))


class DatabaseInterface(object):
    def __init__(self, fname):
        self.fname = fname
        self._ortholog_buffer = []

    def __enter__(self):
        self.con = sqlite3.connect(self.fname)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.commit()
        self.con.close()

    def commit(self):
        self.con.commit()

    def add_reference_proteomes(self, mapping):

        def yield_uniprot_proteins():
            goff = mapping['Goff']
            species = mapping['species']
            for xref, prot_nr in mapping['mapping'].items():
                if RE_UP.match(xref):
                    gnr = bisect_right(goff, prot_nr - 1)
                    yield prot_nr, xref, species[gnr - 1]

        cur = self.con.cursor()
        cur.execute("""DROP TABLE IF EXISTS proteomes""")
        cur.execute("""CREATE TABLE proteomes (
                         prot_nr INT, 
                         uniprot_id CHAR(10), 
                         species CHAR(5)
                       )""")
        cur.executemany("INSERT INTO proteomes VALUES (?,?,?)", yield_uniprot_proteins())
        self.commit()

    def create_pairwise_ortholog_table(self):
        cur = self.con.cursor()
        cur.execute("""DROP TABLE IF EXISTS orthologs""")
        cur.execute("""CREATE TABLE orthologs (
                           prot_nr1 INT , 
                           prot_nr2 INT
                       )""")
        self.commit()

    def create_index_of_orthologs(self):
        logger.info("creating index of orthologs...")
        cur = self.con.cursor()
        cur.execute("CREATE INDEX pair ON orthologs (prot_nr1, prot_nr2)")
        logger.info("finished indexing")
        self.commit()

    def add_orthologs(self, p1, p2):
        self._ortholog_buffer.extend([(p1, p2), (p2, p1)])
        if len(self._ortholog_buffer) > 200000:
            self.flush()

    def flush(self):
        if len(self._ortholog_buffer) > 0:
            self.con.cursor().executemany(
                "INSERT INTO orthologs VALUES (?,?)",
                self._ortholog_buffer)
            self.commit()
            self._ortholog_buffer = []

    def get_orthologs_of(self, prot_nr):
        cur = self.con.cursor()
        cur.execute("SELECT prot_nr2 FROM orthologs WHERE prot_nr1 == ? ORDER BY prot_nr2", (prot_nr, ))
        return [z[0] for z in cur.fetchall()]

    def iter_all_orthologs(self):
        cur = self.con.cursor()
        cur.execute("SELECT DISTINCT * FROM orthologs ORDER BY prot_nr1, prot_nr2")
        cur.arraysize = 50000
        cur_prot, orths = None, []
        while True:
            chunk = cur.fetchmany()
            if len(chunk) == 0:
                break
            for p1, p2 in chunk:
                if p1 != cur_prot:
                    if cur_prot is not None:
                        yield cur_prot, orths
                    cur_prot = p1
                    orths = []
                orths.append(p2)
        if len(orths) > 0:
            yield cur_prot, orths



def identify_input_type_and_parse(fpath, mapping_data):
    with auto_open(fpath, 'rb') as fh:
        head = fh.read(20)

    with DatabaseInterface("orthologs.db") as db:
        db.add_reference_proteomes(mapping_data)
        db.create_pairwise_ortholog_table()

        if head.startswith(b'<?xml') or head.startswith(b'<ortho'):
            with auto_open(fpath, 'rb') as fh:
                processor = PairwiseOrthologRelationExtractor(mapping_data, db)
                parse_orthoxml(fh, processor)
        else:
            with auto_open(fpath, 'rt') as fh:
                for p1, p2 in parse_tsv(fh, mapping_data):
                    db.add_orthologs(p1, p2)
        db.create_index_of_orthologs()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Pairwise relations from uploaded data")
    parser.add_argument('mapping', help="Path to mapping.json of proper QfO dataset")
    parser.add_argument('input_rels', help="Path to input relation file. either tsv or orthoxml")
    parser.add_argument('--out', help="Path to output file")
    parser.add_argument('--log', help="Path to log file. Defaults to stderr")
    parser.add_argument('-d', '--debug', action="store_true", help="Set logging to debug level")
    conf = parser.parse_args()

    log_conf = {'level': logging.INFO, 'format': "%(asctime)-15s %(levelname)-7s: %(message)s"}
    if conf.log is not None:
        log_conf['filename'] = conf.log
    if conf.debug:
        log_conf['level'] = logging.DEBUG
    logging.basicConfig(**log_conf)

    mapping_data = load_mapping(conf.mapping)
    identify_input_type_and_parse(conf.input_rels, mapping_data)
    nr_genes_in_reference_set = mapping_data['Goff'][-1]
    tot_pred = 0
    with DatabaseInterface("orthologs.db") as dbi:
        with open(conf.out, 'w') as fh:
            per_prot_ortholog_iter = dbi.iter_all_orthologs()
            nxt_prot, orths = next(per_prot_ortholog_iter)
            for i in range(1, nr_genes_in_reference_set + 1):
                if nxt_prot < i:
                    try:
                        nxt_prot, orths = next(per_prot_ortholog_iter)
                    except StopIteration:
                        nxt_prot, orths = nr_genes_in_reference_set + 2, []
                if nxt_prot > i:
                    orthologs = []
                elif nxt_prot == i:
                    orthologs = [str(z) for z in orths]
                else:
                    raise RuntimeError("must not happen. Proteins not sorted?")
                fh.write("<E><OE>{}</OE><VP>[{}]</VP><SEQ>{}</SEQ></E>\n"
                         .format(i, ",".join(orthologs), encode_nr_as_seq(i)))
                tot_pred += len(orthologs)
    logger.info("*** Successfully extracted {} pairwise relations from uploaded predictions"
                .format(tot_pred / 2))
