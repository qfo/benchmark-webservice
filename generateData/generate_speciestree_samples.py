import time

import dendropy
import random
import os
import Bio.Phylo
import io
import logging

logger = logging.getLogger('tree-sampler')


def is_bifurcating(tree):
    for n in tree.preorder_node_iter():
        if n.num_child_nodes() > 2:
            return False
    return True


def shuffle_children_order(tree:dendropy.Tree):
    for nd in tree.postorder_internal_node_iter():
        nd._child_nodes.sort(key=lambda n: random.random())


def sample_cases(newick_tree, nr_samples, tree_size, exclude=None):
    t = dendropy.Tree.get(data=newick_tree, schema="newick")
    for k, top_clade_node in enumerate(t.seed_node.child_nodes()):
        for l in top_clade_node.leaf_iter():
            l.taxon.annotations.add(k)
    if exclude is None:
        exclude = []
    all_taxa = [tax for tax in t.taxon_namespace if tax.label not in exclude]

    cases = []
    lst_time = 0
    MAX_TRIALS_WITHOUT_PROGRESS = rem_trials = 20000
    while rem_trials > 0 and len(cases) < nr_samples:
        if time.time() - lst_time > 30:
            logger.info("cur_samplesize: {}; {} unsuccessful consecutive trials"
                        .format(len(cases), MAX_TRIALS_WITHOUT_PROGRESS - rem_trials))
            lst_time = time.time()
        rem_trials -= 1
        sample = random.sample(all_taxa, tree_size)
        cov_clades = {s.annotations[0] for s in sample}
        if len(cov_clades) < 2:
            continue

        candidate = t.extract_tree_with_taxa(sample)
        if is_bifurcating(candidate):
            shuffle_children_order(candidate)
            cases.append(candidate)
            rem_trials = MAX_TRIALS_WITHOUT_PROGRESS
    if rem_trials <= 0:
        raise ValueError("too many trials without successful sampling. Too ambitious parameters?")
    return cases


def extract_relevant_newick_tree(fn_phyloxml, clade):
    with open(fn_phyloxml, 'rt') as fh:
        tree = Bio.Phylo.read(fh, 'phyloxml')

    target_clade = tree if clade == 'LUCA' else next(tree.find_clades(target=clade))
    for n in target_clade.get_terminals():
        n.name = n.taxonomy.code

    buf = io.StringIO()
    Bio.Phylo.write(target_clade, buf, 'newick')
    return buf.getvalue()


if __name__ == "__main__":
    import argparse
    clades = {'Luca': 'LUCA', 'Fun': 'Fungi', 'Euk': 'Eukaryota', 'Ver': 'Euteleostomi'}

    parser = argparse.ArgumentParser(description="Compute relevant species samples for a certain clade")
    parser.add_argument('clade', 
                        help="Clade for which the tree samples should be generated. "
                             "Should be one of 'Luca', 'Fun', 'Euk' or 'Ver'",
                        choices=list(clades.keys()))
    parser.add_argument('--nr-samples', '-N', default=50000, type=int,
                        help="nr of tree samples to be generated, defaults to 50k")
    parser.add_argument('--tree-size', '-s', default=10, type=int,
                        help="nr of taxa per tree, defaults to 10.")
    parser.add_argument('--out', default="/refset",
                        help="directory where output file is stored. The directory "
                             "must previously exist. It defaults to '/refset'.")
    parser.add_argument('-v', action='count', default=0,
                        help="increase verbosity of program. add -vv for debug level")
    parser.add_argument('--exclude', default=None, nargs="*",
                        help="species codes to exclude")
    parser.add_argument('treefile', help="species tree file in phyloxml format")
    conf = parser.parse_args()
    logging.basicConfig(level=30 - 10 * min(conf.v, 2),
                        format='%(asctime)-15s %(name)s %(levelname)-8s: %(message)s')
    logger.info(str(conf))
    lab = conf.clade
    clade = clades[lab]
    newick = extract_relevant_newick_tree(conf.treefile, clade)
    samples = sample_cases(newick, conf.nr_samples, conf.tree_size, exclude=conf.exclude)
    with open(os.path.join(conf.out, 'species_tree_samples_{}.nwk'.format(lab)), 'wt') as fh:
        for t in samples:
            t.write(file=fh, schema='newick')


