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
from io import BytesIO
import bz2
import gzip
import logging
import JSON_templates

logger = logging.getLogger("validator")


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


def parse_orthoxml(fh, valid_ids, excluded_ids):
    nsmap = {}
    og_level = 0
    in_species = False
    nr_species_done = 0
    nr_excluded_genes = 0
    max_invalid_ids = 50

    def fixtag(ns, tag):
        return "{" + nsmap[ns] + "}" + tag

    logger.info("start mapping of orthoxml formatted input file")
    for event, elem in etree.iterparse(fh, events=('start-ns', 'start', 'end')):
        if event == 'start-ns':
            ns, url = elem
            nsmap[ns] = url
        elif event == 'start':
            if elem.tag == fixtag('', 'orthologGroup'):
                assert not in_species
                og_level += 1
            elif elem.tag == fixtag('', 'groups'):
                assert nr_species_done > 0
            elif elem.tag == fixtag('', 'species'):
                assert not in_species
                in_species = True
        if event == 'end':
            if elem.tag == fixtag('', 'orthologGroup'):
                og_level -= 1
                assert og_level >= 0
            elif elem.tag == fixtag('', 'species'):
                assert in_species
                in_species = False
                nr_species_done += 1
            elif elem.tag == fixtag('', 'gene'):
                try:
                    if elem.get('protId') not in valid_ids:
                        if elem.get('protId') not in excluded_ids:
                            max_invalid_ids -= 1
                            if max_invalid_ids < 0:
                                raise AssertionError(
                                    'Too many invalid crossreferences found. Did you select the right reference dataset?')
                        else:
                            logger.debug("excluding protein \"{}\" from the benchmark analysis".format(elem.get('protId')))
                            nr_excluded_genes += 1
                except KeyError:
                    raise AssertionError('<gene> elements must encode xref in "protId" attribute')
            # we can clear all elements right away
            elem.clear()
    assert not in_species
    assert og_level == 0
    assert nr_species_done > 0
    if nr_excluded_genes > 0:
        logger.info("Excluded {} genes form the predictions (excluded species)".format(nr_excluded_genes))
    return True


def parse_tsv(fh, valid_ids, excluded_ids):
    logger.info("trying to read as tsv file")
    max_errors = 5
    invalid_ids = set([])
    reported_excluded = set([])
    dialect = csv.Sniffer().sniff(fh.read(2048))
    fh.seek(0)
    csv_reader = csv.reader(fh, dialect)

    def check_if_valid_id(id_):
        if id_ not in valid_ids:
            if id_ in excluded_ids:
                if not id_ in reported_excluded:
                    reported_excluded.add(id_)
                    logger.debug("protein \"{}\" is excluded from benchmarking (but part of reference proteomes set).")
                    return
            if id_ not in invalid_ids:
                invalid_ids.add(id_)
                if len(invalid_ids) > 50:
                    raise AssertionError(
                        'Too many invalid crossreferences found. Did you select the right reference dataset?')

    line_nr = 0
    for line_nr, row in enumerate(csv_reader):
        if len(row) < 2:
            logger.warning("skipping relation on line {} ({})"
                           .format(line_nr, row))
            max_errors -= 1
            if max_errors < 0:
                raise AssertionError("Too many lines with less than 2 elements")
            continue
        for z in row[:2]:
            check_if_valid_id(z)
    if line_nr < 100:
        raise AssertionError("Too few ortholog pairs to be analysed")
    if len(reported_excluded) > 0:
        logger.info("excluded {} genes from the predictions (excluded species)"
                    .format(len(reported_excluded)))


def identify_input_type_and_validate(fpath, valid_ids, excluded_ids):
    with auto_open(fpath, 'rb') as fh:
        head = fh.read(20)

    if head.startswith(b'<?xml') or head.startswith(b'<ortho'):
        try:
            with auto_open(fpath, 'rb') as fh:
                parse_orthoxml(fh, valid_ids, excluded_ids)
        except AssertionError as e:
            logger.error('input file is not a valid orthoxml file: {}'.format(e))
            return False

    else:
        try:
            with auto_open(fpath, 'rt') as fh:
                parse_tsv(fh, valid_ids, excluded_ids)
        except AssertionError as e:
            logger.error('input file is not a valid tab-separated file: {}'.format(e))
            return False
    return True


def write_participant_dataset_file(outfn, participant_id, community, challenges, is_valid):
    data_id = community + ":" + participant_id + "_P"
    challenges = challenges.split() if isinstance(challenges, str) else challenges
    output_json = JSON_templates.write_participant_dataset(data_id, community, challenges,
                                                           participant_id, is_valid)
    with open(outfn, 'wt') as fout:
        json.dump(output_json, fout, sort_keys=True, indent=4, separators=(',', ': '))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract Pairwise relations from uploaded data")
    parser.add_argument('mapping', help="Path to mapping.json of proper QfO dataset")
    parser.add_argument('input_rels', help="Path to input relation file. either tsv or orthoxml")
    parser.add_argument('-d', '--debug', action="store_true", help="Set logging to debug level")
    parser.add_argument('-c', '--com', required=True, help="Name or OEB permanent ID for the benchmarking community")
    parser.add_argument('--challenges_ids', default=[], help="List of benchmarks that will be run")
    parser.add_argument('-p', '--participant', required=True, help="Name of the tool")
    parser.add_argument('-o', '--out', required=True, help="Output filename for validation json")
    conf = parser.parse_args()

    log_conf = {'level': logging.INFO, 'format': "%(asctime)-15s %(levelname)-7s: %(message)s"}
    if conf.debug:
        log_conf['level'] = logging.DEBUG
    logging.basicConfig(**log_conf)

    mapping_data = load_mapping(conf.mapping)
    excluded_ids = mapping_data['excluded_ids'] if 'excluded_ids' in mapping_data else set([])
    is_valid = identify_input_type_and_validate(conf.input_rels, mapping_data['mapping'], excluded_ids)
    write_participant_dataset_file(conf.out, conf.participant, conf.com, conf.challenges_ids, is_valid)
    if not is_valid:
        sys.exit("ERROR: Submitted data does not validate against any reference data! Please check "+conf.out )
