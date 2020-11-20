#!/usr/bin/env python3

import json
import os
from argparse import ArgumentParser


def write_assessment_file(fpath, *assessment_stubs):
    with open(fpath, 'wt') as fout:
        json.dump(list(assessment_stubs), fout)


def make_assessment_stub(metric, metric_value, metric_error, config):
    id_ = "{}:{}_{}_{}_A".format(config.community_id, config.challenge_id, metric, config.participant_id)
    data = {
        "_id": id_,
        "community_id": config.community_id,
        "challenge_id": config.challenge_id,
        "participant_id": config.participant_id,
        "type": "assessment",
        "metrics": {
            "metric_id": metric,
            "value": metric_value,
            "stderr": metric_error,
        }
    }
    return data


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-p", "--participant-id", required=True,
                        help="name of the tool/participant")
    parser.add_argument("-c", "--community-id", required=True,
                        help="community_id, Name or OEB permanent ID for the benchmarking community")
    parser.add_argument("-b", "--challenge-id", required=True, help="id/name of the benchmark")
    parser.add_argument("-r", "--reference-groups", required=True,
                        help="file containing the reference group data")
    parser.add_argument("-g", "--predicted-groups", required=True,
                        help="file containing the predicted groups in flat format (one group per line)")
    parser.add_argument("-a", "--assessment-out", required=True,
                        help="file where the json assessment file should be written")
    parser.add_argument("-o", "--out", required=True,
                        help="output file containing the detailed raw benchmark results")

    conf = parser.parse_args()

    # reference data (reference groups as defined) can be loaded from conf.reference_groups

    # compute results
    # results = .... computes e.g. TruePositiveRate & false positive rate
    write_assessment_file(conf.assessment_out,
        make_assessment_stub("FPR", 0.8, 0.20, conf),
        make_assessment_stub("TPR", 0.9, 0.08, conf)
    )

    # if possible, also write for each reference group the missing and wrong proteins to
    # conf.out file.
    os.makedirs(os.path.dirname(conf.out), exist_ok=True)
    with open(conf.out, 'wt') as fh:
        fh.write('#GroupNr\tExp\tFound\tWrong\tMissing\tIncorrect\n')
        fh.write("Group1\t10\t7\t1\tP52352,P62235,Q52156\tP62229\n")
        fh.write("Group2\t60\t59\t0\tP12345\t\n")
