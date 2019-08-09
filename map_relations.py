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
import os
import re
from io import BytesIO
import bz2
import gzip
import itertools
import logging
logger = logging.getLogger("relations-processor")


# File opening. This is based on the example on SO here:
# http://stackoverflow.com/a/26986344
fmagic = {b'\x1f\x8b\x08': gzip.open,
          b'\x42\x5a\x68': bz2.BZ2File}


def auto_open(fn, *args, **kwargs):
    """function to open regular or compressed files for read / write.

    This function opens files based on their "magic bytes". Supports bz2
    and gzip. If it finds neither of these, presumption is it is a
    standard, uncompressed file.

    Example::

        with auto_open("/path/to/file/maybe/compressed", mode="rb") as fh:
            fh.read()

        with auto_open("/tmp/test.txt.gz", mode="wb") as fh:
            fh.write("my big testfile")

    :param fn: either a string of an existing or new file path, or
        a BytesIO handle
    :param **kwargs: additional arguments that are understood by the
        underlying open handler
    :returns: a file handler
    """
    if isinstance(fn, BytesIO):
        return fn

    if os.path.isfile(fn) and os.stat(fn).st_size > 0:
        with open(fn, 'rb') as fp:
            fs = fp.read(max([len(x) for x in fmagic]))
        for (magic, _open) in fmagic.items():
            if fs.startswith(magic):
                return _open(fn, *args, **kwargs)
    else:
        if fn.endswith('gz'):
            return gzip.open(fn, *args, **kwargs)
        elif fn.endswith('bz2'):
            return bz2.BZ2File(fn, *args, **kwargs)
    return open(fn, *args, **kwargs)


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


def load_IDIndex(path):
    pat = re.compile(r"<E><KEY>'(?P<key>.*)'</KEY>.*<VALUE>(?P<val>.*)</VALUE>")
    lookup = {}
    with auto_open(path, 'rt') as fh:
        for line in fh:
            m = pat.match(line)
            if m is not None:
                lookup[m.group('key')] = int(m.group('val'))
    logger.info("loaded lookup table with {} valid crossreferences for {} distinct proteins"
                .format(len(lookup), len(frozenset(lookup.values()))))
    return lookup


def load_mapping(path):
    with auto_open(path, 'rb') as fh:
        data = json.loads(fh.read().decode('utf-8'))
    return data


def unique(seq):
    """Return the elements of a list uniquely while preserving the order

    :param list seq: a list of hashable elements
    :returns: new list with first occurence of elements of seq"""
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


class PairwiseOrthologRelationExtractor(object):
    def __init__(self, mapping_data):
        self.valid_id_map = mapping_data['mapping']
        self.internal_genome_offs = mapping_data['Goff']
        self.species_order = mapping_data['species']
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
                logger.warning("protId {} of gene(id={}) (in species {}) is not known in this dataset"
                               .format(gene_prot_id, gene_id, genome_node.get('name')))
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

    def extract_pairwise_relations(self, node):
        rels = []

        def _rec_extract(node):
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
                                rels.append((gId1, gId2))
                nodes = set.union(*nodes_of_children)
                return nodes
            else:
                return set([])
        nodes = _rec_extract(node)
        logger.debug("extracting {} pairwise orthologous relations from toplevel group {} with {} valid genes"
                     .format(len(rels), node.get('id', 'n/a'), len(nodes)))
        self.processed_stats['processed_toplevel'] += 1
        self.processed_stats['relations'] += len(rels)
        if time() - self.processed_stats['last'] > 20:
            logger.info("processed {} toplevel orthologGroups with {} induced pairwise relations"
                        .format(self.processed_stats['processed_toplevel'],
                                self.processed_stats['relations']))
            self.processed_stats['last'] = time()
        return rels


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
                    yield from processor.extract_pairwise_relations(elem)
                    elem.clear()
            elif elem.tag == fixtag('', 'species'):
                if not processor.add_genome_genes(elem):
                    sys.exit(2)
                elem.clear()


def parse_tsv(fh, mapping_data):
    logger.info("start mapping of tsv formatted input data")
    valid_id_map = mapping_data['mapping']
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
            logger.warning("relation {} contains unknown ID: {}".format(row, unkn))


def identify_input_type_and_parse(fpath, mapping_data):
    with auto_open(fpath, 'rb') as fh:
        head = fh.read(20)

    if head.startswith(b'<?xml') or head.startswith(b'<ortho'):
        with auto_open(fpath, 'rb') as fh:
            processor = PairwiseOrthologRelationExtractor(mapping_data)
            yield from parse_orthoxml(fh, processor)
    else:
        with auto_open(fpath, 'rt') as fh:
            yield from parse_tsv(fh, mapping_data)


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


    #valid_id_map = load_IDIndex(conf.IDIndex)
    mapping_data = load_mapping(conf.mapping)
    predictions = [[] for _ in range(mapping_data['Goff'][-1] + 1)]
    tot_pred = 0
    for x, y in identify_input_type_and_parse(conf.input_rels, mapping_data):
        predictions[x].append(y)
        predictions[y].append(x)
        tot_pred += 1

    removed_duplicates = 0
    with open(conf.out, 'w') as fh:
        for i in range(1, len(predictions)):
            orthologs = unique([str(z) for z in sorted(predictions[i])])
            removed_duplicates += (len(predictions[i]) - len(orthologs))
            fh.write("<E><OE>{}</OE><VP>[{}]</VP><SEQ>{}</SEQ></E>\n"
                     .format(i, ",".join(orthologs), encode_nr_as_seq(i)))
    logger.info("*** Successfully extracted {} pairwise relations from uploaded predictions"
                .format(tot_pred))
    if removed_duplicates > 0:
        logger.info('    Removed {:.0f} duplicated pairwise relations'.format(removed_duplicates/2))
