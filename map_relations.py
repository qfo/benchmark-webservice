#!/usr/bin/env python3
import csv
import math

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
    logger.info("loaded valid_id_map with {} xrefs".format(len(lookup)))
    return lookup


class PairwiseOrthologRelationExtractor(object):
    def __init__(self, valid_id_map):
        self.valid_id_map = valid_id_map
        self.genome_cnt = 0
        self.generef_to_internal_id = {}
        self.internal_to_genome_nr = {}

    def add_genome_genes(self, genome_node):
        self.genome_cnt += 1
        for gene in genome_node.findall('.//{http://orthoXML.org/2011/}gene'):
            gene_id = gene.get('id')
            gene_prot_id = gene.get('protId')
            try:
                internal_id = self.valid_id_map[gene_prot_id]
                self.generef_to_internal_id[int(gene_id)] = internal_id
                self.internal_to_genome_nr[internal_id] = self.genome_cnt
            except KeyError:
                logger.warning("protId {} of gene(id={}) is not known in this dataset"
                               .format(gene_prot_id, gene_id))

    def extract_pairwise_relations(self, node):
        rels = []
        def _rec_extract(node):
            if node.tag == "{http://orthoXML.org/2011/}geneRef":
                try:
                    return set([self.generef_to_internal_id[int(node.get('id'))]])
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
        logger.info("extracting {} pairwise orthologous relations from toplevel group {} with {} valid genes"
                    .format(len(rels), node.get('id', 'n/a'), len(nodes)))
        return rels


def parse_orthoxml(fh, processor):
    nsmap = {}
    og_level = 0

    def fixtag(ns, tag):
        return "{" + nsmap[ns] + "}" + tag

    for event, elem in etree.iterparse(fh, events=('start-ns', 'start', 'end')):
        if event == 'start-ns':
            ns, url = elem
            nsmap[ns] = url
        if event == 'start' and elem.tag == fixtag('', 'orthologGroup'):
            og_level += 1
        if event == 'end':
            if elem.tag == fixtag('', 'orthologGroup'):
                og_level -= 1
                if og_level == 0:
                    yield from processor.extract_pairwise_relations(elem)
                    elem.clear()
            elif elem.tag == fixtag('', 'species'):
                processor.add_genome_genes(elem)
                elem.clear()


def parse_tsv(fh, valid_id_map):
    dialect = csv.Sniffer().sniff(fh.read(2048))
    fh.seek(0)
    csv_reader = csv.reader(fh, dialect)
    for line_nr, row in enumerate(csv_reader):
        if len(row) < 2:
            logger.warning("skipping relation on line {} ({})"
                           .format(line_nr, row))
            continue
        try:
            yield valid_id_map[row[0]], valid_id_map[row[1]]
        except KeyError:
            unkn = list(itertools.filterfalse(lambda x: x in valid_id_map, row[:2]))
            logger.warning("relation {} contains unknown ID: {}".format(row, unkn))


def identify_input_type_and_parse(fpath, valid_id_mapping):
    with auto_open(fpath, 'rb') as fh:
        head = fh.read(20)

    if head.startswith(b'<?xml') or head.startswith(b'<ortho'):
        with auto_open(fpath, 'rb') as fh:
            processor = PairwiseOrthologRelationExtractor(valid_id_mapping)
            yield from parse_orthoxml(fh, processor)
    else:
        with auto_open(fpath, 'rt') as fh:
            yield from parse_tsv(fh, valid_id_map)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Pairwise relations from uploaded data")
    parser.add_argument('IDIndex', help="Path to IDIndex of proper QfO dataset")
    parser.add_argument('input_rels', help="Path to input relation file. either tsv or orthoxml")
    parser.add_argument('--out', help="Path to output file")
    logging.basicConfig(level=logging.INFO)

    conf = parser.parse_args()

    valid_id_map = load_IDIndex(conf.IDIndex)
    predictions = [[] for _ in range(max(valid_id_map.values())+1)]
    tot_pred = 0
    for x, y in identify_input_type_and_parse(conf.input_rels, valid_id_map):
        predictions[x].append(y)
        predictions[y].append(x)
        tot_pred += 1
    with open(conf.out, 'w') as fh:
        for i in range(1, len(predictions)):
            fh.write("<E><OE>{}</OE><VP>[{}]</VP><SEQ>{}</SEQ></E>\n"
                     .format(i, ",".join([str(z) for z in sorted(predictions[i])]),
                             encode_nr_as_seq(i)))