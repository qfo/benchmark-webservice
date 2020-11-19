#!/usr/bin/env python3
import collections
import csv
import json
import math
import sys
from bisect import bisect_right
from time import time
import xml.etree.ElementTree as etree
import os
import re
from io import BytesIO
import Bio.Phylo
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


class Clade:
    def __init__(self, fn_phyloxml, clade):
        with open(fn_phyloxml, 'rt') as fh:
            tree = Bio.Phylo.read(fh, 'phyloxml')
        target_clade = next(tree.find_clades(target=clade))
        self.species = frozenset([n.taxonomy.code for n in target_clade.get_terminals()])
        self.taxid = target_clade.taxonomy.id.value
        self.name = clade

    def all_in_clade(self, genes):
        return set(g.species for g in genes).issubset(self.species)

    def does_match(self, name_or_id):
        return name_or_id == self.name or name_or_id == self.taxid


Gene = collections.namedtuple("Gene", "prot_id species")


class GroupExtractor(object):
    def __init__(self, mapping_data, target_clade:Clade):
        self.valid_id_map = mapping_data['mapping']
        self.internal_genome_offs = mapping_data['Goff']
        self.species_order = mapping_data['species']
        self.processed_stats = {'last': time(), 'processed_toplevel': 0}
        self.target_clade = target_clade
        self.genes = {}

    def _genome_of_protein_id(self, prot_id):
        internal_id = self.valid_id_map[prot_id]
        gnr = bisect_right(self.internal_genome_offs, internal_id - 1)
        return self.species_order[gnr - 1]

    def add_genome_genes(self, genome_node):
        generef_2_xref = {}
        for gene in genome_node.findall('.//{http://orthoXML.org/2011/}gene'):
            gene_id = gene.get('id')
            gene_prot_id = gene.get('protId')
            try:
                genome = self._genome_of_protein_id(gene_prot_id)
                generef_2_xref[gene_id] = Gene(gene_prot_id, genome)
            except KeyError:
                logger.warning("protId {} of gene(id={}) (in species {}) is not known in this dataset"
                               .format(gene_prot_id, gene_id, genome_node.get('name')))
        cnts = collections.Counter(g.species for g in generef_2_xref.values())
        if len(cnts) > 1:
            logger.error("Not all crossreferences used in species '{}' map to the same species: {}"
                         .format(genome_node.get('name'), cnts))
            return False

        self.genes.update(generef_2_xref)
        return True

    def _collect_genes(self, node):
        genes = []
        for child in node.iter():
            if child.tag == "{http://orthoXML.org/2011/}geneRef":
                genes.append(self.genes[child.get('id')])
            elif child.tag == "{http://orthoXML.org/2011/}orthologGroup":
                genes.extend((n for n in child.text if isinstance(n, Gene)))
        return genes

    def merge_children(self, node):
        genes = self._collect_genes(node)
        node.clear()
        node.text = genes

    def get_group(self, node):
        return node.text

    def analyze_and_yield_groups(self, node, is_toplevel=False):
        genes = self._collect_genes(node)
        if self.target_clade.all_in_clade(genes):
            if is_toplevel:
                logger.debug("dumping toplevel hog with {} genes (hog_id: {})".format(len(genes), node.get('id')))
                yield genes
            else:
                node.clear()
                node.text = genes
        else:
            for group in node.iter("{http://orthoXML.org/2011/}orthologGroup"):
                if group == node:
                    continue
                if self.target_clade.all_in_clade(group.text):
                    logger.debug("found hog with {} genes".format(len(group.text)))
                    yield group.text
            node.clear()
            node.text = genes


def parse_orthoxml(fh, processor:GroupExtractor):
    nsmap = {}
    og_level = 0
    extract_at_depth = -2

    def fixtag(ns, tag):
        return "{" + nsmap[ns] + "}" + tag

    logger.info("start mapping of orthoxml formatted input file")
    for event, elem in etree.iterparse(fh, events=('start-ns', 'start', 'end')):
        if event == 'start-ns':
            ns, url = elem
            nsmap[ns] = url
        elif event == 'start' and elem.tag == fixtag('', 'orthologGroup'):
            og_level += 1
        elif event == 'start' and elem.tag == fixtag('', 'property'):
            if og_level > 0 and elem.get('name').lower() in ("taxid", "taxrange", "taxonomic_range", "taxon_id", "ncbitaxid"):
                if processor.target_clade.does_match(elem.get('value').lower()):
                    extract_at_depth = og_level
        elif event == 'end':
            if elem.tag == fixtag('', 'orthologGroup'):
                og_level -= 1
                if extract_at_depth == -2:
                    # no level annotations, we need to check ourself if we are at the right level
                    yield from processor.analyze_and_yield_groups(elem, is_toplevel=(og_level == 0))
                elif extract_at_depth >= 0:
                    # we have taxonomic annotations. combine children and yield group in case
                    # we are at the right level
                    processor.merge_children(elem)
                    if og_level == extract_at_depth:
                        logger.debug("dumping annotated group with {} genes".format(len(elem.text)))
                        yield processor.get_group(elem)
                        elem.clear()
                        extract_at_depth = -1
                if og_level == 0:
                    elem.clear()
            elif elem.tag == fixtag('', 'species'):
                if not processor.add_genome_genes(elem):
                    sys.exit(2)
                elem.clear()


def identify_input_type_and_parse(fpath, processor):
    with auto_open(fpath, 'rb') as fh:
        head = fh.read(20)

    if head.startswith(b'<?xml') or head.startswith(b'<ortho'):
        with auto_open(fpath, 'rb') as fh:
            yield from parse_orthoxml(fh, processor)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Pairwise relations from uploaded data")
    parser.add_argument('mapping', help="Path to mapping.json of proper QfO dataset")
    parser.add_argument('input_rels', help="Path to input relation file. either tsv or orthoxml")
    parser.add_argument('--clade', required=True, help="Taxonomic level at which to extract the groups")
    parser.add_argument('--taxonomy', required=True, help="Path to the lineage taxonomy in phyloxml format")
    parser.add_argument('--out', required=True, help="Path to output file")
    parser.add_argument('--log', help="Path to log file. Defaults to stderr")
    parser.add_argument('-d', '--debug', action="store_true", help="Set logging to debug level")
    conf = parser.parse_args()

    log_conf = {'level': logging.INFO, 'format': "%(asctime)-15s %(levelname)-7s: %(message)s"}
    if conf.log is not None:
        log_conf['filename'] = conf.log
    if conf.debug:
        log_conf['level'] = logging.DEBUG
    logging.basicConfig(**log_conf)

    clade = Clade(conf.taxonomy, conf.clade)
    mapping_data = load_mapping(conf.mapping)
    processor = GroupExtractor(mapping_data, clade)

    with open(conf.out, 'w') as fh:
        for grp_nr, group in enumerate(identify_input_type_and_parse(conf.input_rels, processor)):
            fh.write("\t".join((gene.prot_id for gene in group)))
            fh.write("\n")

    logger.info("*** Successfully extracted {} groups at the {} level"
                .format(grp_nr, conf.clade))
