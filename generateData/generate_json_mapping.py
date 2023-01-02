import os
import re
import gzip
import json
import argparse


def parse_db(fn, exclude=None):
    exclude = [] if exclude is None else exclude
    with open(fn, 'rt') as fh:
        curOS = ""
        genomes = []
        Goff = []
        mappings = {}
        excluded_ids = set([])

        parser = re.compile(r'<E><OS>(?P<os>\w*)<\/OS><MAPIDS>(?P<ids>.*)<\/MAPIDS>.*<SEQ>.*<\/SEQ><\/E>')
        for off, line in enumerate(fh):
            m = parser.match(line)
            if not m:
                raise ValueError("Invalid format on database {} on line {}: {}".format(fn, off+1, line))
            if m.group('os') != curOS:
                curOS = m.group('os')
                genomes.append(curOS)
                Goff.append(off)
            for cur_id in m.group('ids').split('; '):
                if curOS in exclude:
                    excluded_ids.add(cur_id)
                    continue
                if cur_id in mappings:
                    mappings[cur_id] = -1
                else:
                    mappings[cur_id] = off + 1
    Goff.append(off + 1)
    to_rem = [k for k, v in mappings.items() if v == -1]
    print("removing {} ids which are not unique".format(len(to_rem)))
    for c in to_rem:
        mappings.pop(c)
    return {'mapping': mappings, 'Goff': Goff, 'species': genomes, 'excluded_ids': list(excluded_ids)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert ServerSeqs.db to mapping.json.gz")
    parser.add_argument('-e', '--exclude', nargs="*", required=False,
                        help="list excluded genomes, that should be ignored for benchmarking. "
                             "The list should contain the relevant OS tags, e.g. UniProtKB "
                             "mnemonic species codes")
    conf = parser.parse_args()

    data = parse_db(os.path.join(os.getenv('QFO_REFSET_PATH'), "ServerSeqs.db"), exclude=conf.exclude)
    with gzip.open(os.path.join(os.getenv("QFO_REFSET_PATH"), "mapping.json.gz"), 'wt', encoding="utf-8", compresslevel=9) as fout:
        json.dump(data, fout)

