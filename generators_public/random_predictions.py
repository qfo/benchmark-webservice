import json
import os
import random
import argparse
import gzip
import re


def generate_random_pairs(ids, nr_predictions):
    id_list = list(ids)
    pairs = set([])
    while len(pairs) < nr_predictions:
        a = random.choice(id_list)
        b = random.choice(id_list)
        if ids[a] != ids[b]:
            if a>b:
                t = a; a = b; b = t
            pairs.add((a,b))
    return pairs


def load_ids(dbfn):
    ids = {}
    entry_re = re.compile(r"<E><OS>(?P<os>\w+)<\/OS>.*<MAPIDS>(?P<ids>[\w; ]+)<\/MAPIDS>")
    up_re = re.compile(r"[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}")
    with open(dbfn, 'rt') as fh:
        cur_os = ""
        for off, line in enumerate(fh):
            m = entry_re.match(line)
            if m:
                if m.group('os') != cur_os:
                    cur_os = m.group('os')
                for cid in m.group('ids').split('; '):
                    if up_re.match(cid):
                        break
                ids[cid] = cur_os
    return ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate random ortholog predictions")
    parser.add_argument('--out', required=True, help="output filename")
    parser.add_argument('-n', '--nr-predictions', default=10000000, type=int, help="number of pairwise orthologs")
    parser.add_argument('--db', help="path to database file (ServerIndexed.db or similar)", required=True)
    conf = parser.parse_args()

    ids = load_ids(conf.db)
    pairs = generate_random_pairs(ids, conf.nr_predictions)
    open_ = gzip.open if conf.out.endswith('.gz') else open
    with open_(conf.out, 'wt') as fout:
        for pair in pairs:
            fout.write('{}\t{}\n'.format(*pair))


