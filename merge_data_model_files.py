#!/usr/bin/env python3

import json
import os
import fnmatch
from argparse import ArgumentParser


def files_in_directory(dir, ext=None):
    for cdir, subdir, files in os.walk(dir):
        for fname in files:
            if ext is None or fname.endswith(ext):
                yield os.path.join(cdir, fname)


def main(participant_data_files, metrics_stub_files, aggregation_stub_dir, aggregation_out_file, model_output_file):
    # collect all aggregation stubs from the aggregation_stub_dir.
    # (containing the summary datapoints for all previous methods)
    aggregation_stubs = list(files_in_directory(aggregation_stub_dir, '.json'))

    # Assuring the output directories do exist
    for path in (model_output_file, aggregation_out_file):
        out_dir = os.path.dirname(os.path.abspath(path))
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

    data_model_file = []
    data_model_file = join_json_files(participant_data_files, data_model_file, "*.json")
    nr_part_stubs = len(data_model_file)
    data_model_file = join_json_files(metrics_stub_files, data_model_file, "*.json")

    #output_file = os.path.join(aggregation_out_dir, 'Assessment_datasets.json')
    with open(aggregation_out_file, 'w') as f:
        json.dump(data_model_file[nr_part_stubs:], f, sort_keys=True, indent=4, separators=(',', ': '))

    # load the aggregation files created in manage_assessment_data.py
    data_model_file = join_json_files(aggregation_stubs, data_model_file, "*.json")

    # write the merged data model file to json output
    # output_file = os.path.join(model_output_dir, "data_model_file.json")
    with open(model_output_file, 'w') as f:
        json.dump(data_model_file, f, sort_keys=True, indent=4, separators=(',', ': '))


def join_json_files(files, data_model_file, file_extension):
    for abs_result_file in files:
        if fnmatch.fnmatch(abs_result_file, file_extension) and os.path.isfile(abs_result_file):
            with open(abs_result_file, mode='r', encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, dict):
                    data_model_file.append(content)
                else:
                    data_model_file.extend(content)
    return data_model_file


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-p", "--participant_data", nargs='*', required=True,
                        help="file(s) that contains the participant json stub (generated by validation step)")
    parser.add_argument("-m", "--metrics_data", nargs='*',
                        help="files containing the benchmark stubs", required=True)
    parser.add_argument("-r", "--results_dir", required=True,
                        help="directory containing the aggregation results stubs of the benchmark")
    parser.add_argument("-a", "--aggregation_file", required=True,
                        help="file where Assessment datasets should be written")
    parser.add_argument("-o", "--output_file", required=True,
                        help="output file where the minimal data model JSON file will be written")

    args = parser.parse_args()
    main(args.participant_data, args.metrics_data, args.results_dir, args.aggregation_file, args.output_file)

