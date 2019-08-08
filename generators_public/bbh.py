#!/usr/bin/env python3

import requests
from typing import List, NamedTuple, Type
import collections
import itertools
import multiprocessing
import operator
import logging
logger = logging.getLogger('bbh')
Match = collections.namedtuple('Match', ["Protein1", "Protein2", "Score", "PamDistance", "Start1", "End1", "Start2",
                                         "End2", "PamVariance", "LogEValue", "PIdent", "Global_Score",
                                         "Global_PamDistance", "Global_PamVariance", "Global_PIdent", "Bitscore"])


def get_genomes(limit=None):
    r = requests.get('http://siblings.ch/api/genomes/', {'limit': limit, 'format': 'json'})
    r.raise_for_status()
    return [e['NCBITaxonId'] for e in r.json()]


def get_protein_ids(genome, limit=None):
    r = requests.get('http://siblings.ch/api/genomes/{}'.format(genome),
                     {'limit': limit, 'cdna': False, 'format': 'json'})
    r.raise_for_status()
    lookup = {e['EntryNr']: e['ID'] for e in r.json()}
    return lookup


def get_matches(genome1, genome2):
    r = requests.get('http://siblings.ch/api/matches/{}/{}/'.format(genome1, genome2),
                     {'format': 'json', 'idtype': 'source'})
    r.raise_for_status()
    matches = r.json()
    values = [Match(*row) for row in matches['data']]
    return values


class FractionOfBestScore:
    frac_of_best = 0.99
    accessor = operator.attrgetter('Score')
    better = operator.gt

    def __init__(self):
        self.candidates = []

    def present(self, m):
        if len(self.candidates) == 0:
            self.candidates.append(m)
        # m.score > best.score * frac  || m.dist < best.dist * frac
        elif self.better(self.accessor(m), self.accessor(self.candidates[0]) * self.frac_of_best):
            # m.score <= best.score  ||  m.dist >= best.dist
            if not self.better(self.accessor(m), self.accessor(self.candidates[0])):
                self.candidates.append(m)
            else:
                # new top hit
                self.candidates.insert(0, m)
                cutoff = self.frac_of_best * self.accessor(m)
                # c.score > new_best.score * frac  | c.dist < new_best.dist * frac
                self.candidates = [c for c in self.candidates if self.better(self.accessor(c), cutoff)]

    def __contains__(self, match):
        return match in self.candidates


class RSD(FractionOfBestScore):
    frac_of_best = 1/0.99
    better = operator.lt
    accessor = operator.attrgetter('Score')


class BitScoreBest(FractionOfBestScore):
    accessor = operator.attrgetter('Bitscore')


class Method:
    def __init__(self, method: Type[FractionOfBestScore], matches: List[Match]):
        self.matches = matches
        self.best_from1 = collections.defaultdict(method)
        self.best_from2 = collections.defaultdict(method)

    def compute_bidirectional_best(self):
        for m in self.matches:
            if not self.is_significant(m):
                continue
            self.best_from1[m.Protein1].present(m)
            self.best_from2[m.Protein2].present(m)

        bets = list(filter(lambda m: (m in self.best_from1[m.Protein1] and
                                      m in self.best_from2[m.Protein2]),
                           self.matches))
        return bets

    def is_significant(self, m: Match):
        return True


def get_bbh_orthologs(pair):
    genome1, genome2 = pair
    logger.info('analysing {} vs {}'.format(genome1, genome2))
    bbh = Method(FractionOfBestScore, get_matches(genome1, genome2))
    return pair, bbh.compute_bidirectional_best()


def get_rsd_orthologs(pair):
    genome1, genome2 = pair
    logger.info('analysing {} vs {}'.format(genome1, genome2))
    rsd = Method(RSD, get_matches(genome1, genome2))
    return pair, rsd.compute_bidirectional_best()


def get_orthologs(fh, method):
    genomes = get_genomes()
    with multiprocessing.Pool(processes=8) as pool:
        work = itertools.combinations(genomes, 2)
        res = pool.imap(method, work)
        for pair, pw in res:
            logger.info('received {} orthologs for {} pair'.format(len(pw), pair))
            for ortholog in pw:
                fh.write("{}\t{}\t{}\n".format(ortholog.Protein1, ortholog.Protein2, ortholog.Score))


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s/%(processName)s - %(message)s')
    parser = argparse.ArgumentParser(description="Extract RSD / BBH orthologs from Siblings")
    parser.add_argument('-o', '--out', type=argparse.FileType('w'), default='-', help='file to store orthologs')
    parser.add_argument('-m', '--method', default='bbh', choices=['bbh', 'rsd'])
    conf = parser.parse_args()

    method = get_bbh_orthologs if conf.method == 'bbh' else get_rsd_orthologs
    get_orthologs(conf.out, method)
