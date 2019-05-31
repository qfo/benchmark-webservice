import dendropy
import random
import math
import Bio.Phylo
import io


def is_bifurcating(tree):
    for n in tree.preorder_node_iter():
        if n.num_child_nodes() > 2:
            return False
    return True


def sample_cases(newick_tree):
    t = dendropy.Tree.get(data=newick_tree, schema="newick")
    all_taxa = list(t.taxon_namespace)

    cases = []
    while len(cases) < 50000:
        nxt_chunk = list(filter(is_bifurcating, [t.extract_tree_with_taxa(random.sample(all_taxa, 10)) for _ in range(100000)]))
        cases.extend(nxt_chunk)
    return cases[0:50000]


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
    clades = {'LUCA': 'LUCA', 'Fun': 'Fungi', 'Euk': 'Eukaryota', 'Ver': 'Euteleostomi'}
    for lab, clade in clades.items():
        newick = extract_relevant_newick_tree('/refset/lineage_tree.phyloxml', clade)
        samples = sample_cases(newick)
        with open('/refset/species_tree_samples_{}.nwk'.format(lab), 'wt') as fh:
            for t in samples:
                t.write(file=fh, schema='newick')


