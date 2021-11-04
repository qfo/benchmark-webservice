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


def get_idpart(sp):
    return sp.rsplit('_', 1)[0]

def get_species(sp):
    s = sp.rsplit('_', 1)[1]
    if s == "RAT":
        s = "RATNO"
    return s


class SwissProtComparerSimple:
    def __init__(self, sp_entries, **kwargs):
        self.sp_entries = sp_entries
        self._init_relations()

    def are_orthologs(self, en1, en2):
        #sp_id1, sp_id2 = tuple(sp_entries[enr].rsplit('_', 1)[0] for enr in (en1, en2))
        #return sp_id1
        return (min(en1, en2), max(en1, en2)) in self.true_orthologs

    def are_non_orthologs(self, en1, en2, **kwargs):
        # check that they have non common prefix, e.g. the sp id starts with a different character
        return self.sp_entries[en1][0] != self.sp_entries[en2][0]

    def _init_relations(self):
        self.true_orthologs = frozenset(self._get_true_orthologs_by_identical_ids())

    def _get_true_orthologs_by_identical_ids(self):
        res = set([])
        sorted_sp_entries = sorted(((v, k) for k, v in self.sp_entries.items()), key=lambda x: get_idpart(x[0]))
        for grp, entries in itertools.groupby(sorted_sp_entries, key=lambda x: get_idpart(x[0])):
            res.update({(min(x[1], y[1]), max(x[1], y[1])) for x, y in itertools.combinations(entries, 2)})
        return res


class SwissProtComparerTaxRangeLimited(SwissProtComparerSimple):
    def __init__(self, sp_entries, species_tree_fn, **kwargs):
        super().__init__(sp_entries, **kwargs)
        self.species_tree = self._load_species_tree(species_tree_fn)
        self._per_fam_species_to_consider = self._extract_per_fam_species_set()

    def _load_species_tree(self, tree_fn):
        with open(tree_fn, 'rt') as fh:
            tree = Bio.Phylo.read(fh, 'phyloxml')
        for n in tree.get_terminals():
            n.name = n.taxonomy.code
        for n in tree.get_nonterminals():
            n.name = n.taxonomy.scientific_name
        buf = io.StringIO()
        Bio.Phylo.write(tree, buf, 'newick')
        tree = dendropy.Tree.get(data=buf.getvalue(), schema="newick")
        return tree

    def _extract_per_fam_species_set(self):
        swissprot_sorted = sorted(self.sp_entries.values(), key=get_idpart)
        per_fam_species = collections.defaultdict(set)
        for fam, prot in itertools.groupby(swissprot_sorted, key=get_idpart):
            prots = list(prot)
            sps = set([get_species(x) for x in prots])
            assert (len(sps) == len(prots))
            if len(prots) > 1:
                mrca = self.species_tree.mrca(taxon_labels=sps)
                tax_range_species = set(l.taxon.label for l in mrca.leaf_iter())
                # remove direct clades from mrca if no annoations and at least 3 leaves
                rem_clades = []
                for c in mrca.child_node_iter():
                    sub_clade_leaves = set(l.taxon.label for l in c.leaf_iter())
                    if len(sub_clade_leaves) > 2 and len(sps.intersection(sub_clade_leaves)) == 0:
                        tax_range_species -= sub_clade_leaves
                        rem_clades.append(c.label)
                per_fam_species[fam] = tax_range_species
                logger.debug("SwissProt \"{}\": present in {}. Propagating to {} excluding {}"
                             .format(fam, sps, mrca.label, rem_clades))
        return per_fam_species

    def are_non_orthologs(self, en1, en2, info1, info2, **kwargs):
        id1, id2 = (get_idpart(sp_entries[en]) for en in (en1, en2))
        org1, org2 = (i.Species for i in (info1, info2))
        res = id1[0] != id2[0] and \
              org2 in self._per_fam_species_to_consider[id1] and \
              org1 in self._per_fam_species_to_consider[id2]
        if id1[0] != id2[0] and logger.isEnabledFor(logging.DEBUG):
            logger.debug("check non-ortholog: {} vs {}; {}:{}; {}:{}; return: {}".
                         format(sp_entries[en1], sp_entries[en2], id1,
                                self._per_fam_species_to_consider[id1],
                                id2,
                                self._per_fam_species_to_consider[id2],
                                res))
        return res


class SwissProtComparerExistingIdInBothSpecies(SwissProtComparerSimple):
    def __init__(self, sp_entries, **kwargs):
        super().__init__(sp_entries, **kwargs)
        self.ids_per_species = self._build_idset_per_species()

    def _build_idset_per_species(self):
        sps = collections.defaultdict(set)
        for en, spid in self.sp_entries.items():
            id_, species = spid.rsplit('_', 1)
            sps[species].add(id_)
        return sps

    def are_non_orthologs(self, en1, en2, info1, info2, **kwargs):
        id1, id2 = (get_idpart(sp_entries[en]) for en in (en1, en2))
        org1, org2 = (i.Species for i in (info1, info2))
        res = id1[0] != id2[0] and id1 in self.ids_per_species[org2] and id2 in self.ids_per_species[org1]
        if id1[0] != id2[0] and logger.isEnabledFor(logging.DEBUG):
            logger.debug("check non-ortholog: {} vs {}: {} in {}: {}; {} in {}: {}; return {}"
                         .format(sp_entries[en1], sp_entries[en2],
                                 id1, org2, id1 in self.ids_per_species[org2],
                                 id2, org1, id2 in self.ids_per_species[org1],
                                 res))
        return res


Protein = collections.namedtuple("Protein", ["Acc", "Species"])


def compute_sp_benchmark(sp_entries, db_path, raw_out, strategy: SwissProtComparerSimple):

    def get_prot_data_for(proteins):
        data = {}
        cur = con.cursor()
        placeholder = ",".join('?'*len(proteins))
        query = f"SELECT * FROM proteomes WHERE prot_nr IN ({placeholder})"
        cur.execute(query, proteins)
        for row in cur.fetchall():
            data[row[0]] = Protein(row[1], row[2])
        return data

    def get_swissprot_orthologs_of(prot_nr):
        cur = con.cursor()
        cur.execute(
            "SELECT DISTINCT prot_nr2 FROM orthologs WHERE prot_nr1 == ? AND prot_nr1 < prot_nr2 ORDER BY prot_nr2",
            (prot_nr,))
        return [z[0] for z in cur.fetchall() if z[0] in sp_entries]

    def write_raw_rels(out, rels, typ):
        for en1, en2 in rels:
            out.write("{}\t{}\t{}\t{}\t{}\n".format(sp_entries[en1], sp_entries[en2], typ,
                                                    protein_infos[en1].Species, protein_infos[en2].Species))

    con = sqlite3.connect(db_path)
    nr_true = len(strategy.true_orthologs)
    missing_true_orthologs = set(strategy.true_orthologs)
    protein_infos = get_prot_data_for(list(sp_entries.keys()))
    
    orthologs_among_sp = 0
    tp = 0
    fp = 0
    for sp_entry in sp_entries:
        orths = get_swissprot_orthologs_of(sp_entry)
        orthologs_among_sp += len(orths)
        false_positives = [(sp_entry, en) for en in orths
                           if strategy.are_non_orthologs(sp_entry, en, info1=protein_infos[sp_entry],
                                                         info2=protein_infos[en])]
        fp += len(false_positives)
        write_raw_rels(raw_out, false_positives, 'FP')

        true_positives = {(sp_entry, en) for en in orths if strategy.are_orthologs(sp_entry, en)}
        tp += len(true_positives)
        write_raw_rels(raw_out, true_positives, 'TP')
        missing_true_orthologs -= true_positives

    write_raw_rels(raw_out, missing_true_orthologs, "FN")
    tpr = tp / nr_true
    ppv = tp / (fp + tp)
    logger.info("TPR: {}; PPV: {}, nr_true: {}".format(tpr, ppv, nr_true))
    metrics = [{"name": "TP", 'value': tp},
               {"name": "Nr orthologs among SwissProt entries", 'value': orthologs_among_sp},
               {"name": "FP", "value": fp},
               {"name": "FN", "value": len(missing_true_orthologs)},
               {"name": "TPR", "value": tpr, "stderr": 1.96 * math.sqrt(tpr * (1 - tpr) / nr_true)},
               {"name": "PPV", "value": ppv, "stderr": 1.96 * math.sqrt(ppv * (1 - ppv) / (fp + tp))},
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
    parser.add_argument('--assessment-out', required=True, help="Path where assessment json file will be stored")
    parser.add_argument('--outdir', required=True, help="Folder to store the raw output file in")
    parser.add_argument('--db', required=True, help="Path to sqlite database with pairwise predictions")
    parser.add_argument('--com', required=True, help="community id")
    parser.add_argument('--sp-entries', required=True, help="Path to textfile with SwissProt IDs")
    parser.add_argument('--participant', required=True, help="Name of participant method")
    parser.add_argument('--strategy', choices=("simple", "clade_limit", "ids_exist_in_both"),
                        default="clade_limit",
                        help="benchmark strategy to use. Simple: negatives are any non-prefix sharing relation, "
                             "Clade_limit: only within clades where ID is used.")
    parser.add_argument('--lineage-tree', help="path to lineage tree in phyloxml format. Used for clade_limit strategy only")
    parser.add_argument('--log', help="Path to log file. Defaults to stderr")
    parser.add_argument('-d', '--debug', action="store_true", help="Set logging to debug level")
    conf = parser.parse_args()

    log_conf = {'level': logging.INFO, 'format': "%(asctime)-15s %(levelname)-7s: %(message)s"}
    if conf.log is not None:
        log_conf['filename'] = conf.log
    if conf.debug:
        log_conf['level'] = logging.DEBUG
    logging.basicConfig(**log_conf)
    logger.info("running swissprot_benchmark with following arguments: {}".format(conf))

    os.makedirs(conf.outdir, exist_ok=True)
    outfn_path = os.path.join(conf.outdir,
                              "SP_{}_{}_raw.txt.gz".format(conf.participant.replace(' ', '-').replace('_', '-'),
                                                           conf.strategy)
                              )
    sp_entries = get_swissprot_entries(conf.mapping, conf.sp_entries)
    if conf.strategy.lower() == "simple":
        strategy = SwissProtComparerSimple(sp_entries)
    elif conf.strategy.lower() == "clade_limit":
        strategy = SwissProtComparerTaxRangeLimited(sp_entries, species_tree_fn=conf.lineage_tree)
    elif conf.strategy.lower() == "ids_exist_in_both":
        strategy = SwissProtComparerExistingIdInBothSpecies(sp_entries)
    else:
        raise Exception("Invalid strategy")

    with auto_open(outfn_path, 'wt') as raw_out_fh:
        res = compute_sp_benchmark(sp_entries, conf.db, raw_out_fh, strategy)
    write_assessment_json_stub(conf.assessment_out, conf.com, conf.participant, res)
