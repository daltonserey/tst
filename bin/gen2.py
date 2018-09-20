#!/usr/bin/env python
# coding: utf-8
"""
TST testcase generator.

This module provides a single public function named create_test_suite
that creates a test suite containing a set of testcases based on a
given specification. The module does not provide any kind of user
interface. Import the function directly as in:

    from gen2 import create_test_suite

Optionally, use the provided main function that imports the 
specification from a file named specs.yaml and prints the test
suite as a json in the output. Run as follows:

    python -m gen2

    or

    python gen2.py
"""
import sys
import os
import yaml
import json
import codecs
import random
import hashlib

import tstlib as tst

from jinja2 import Template
from datagen import DataGenerator

dg = DataGenerator()

def create_test_suite(spec, include_all_tests):
    # read test cases and parameters specification
    cases_spec = spec['cases']
    parameters = spec.get('parameters', [])

    # read templates
    input_template = Template(spec['input_template'], keep_trailing_newline=True)
    output_template = Template(spec.get('output_template', ''), keep_trailing_newline=True)

    test_suite, cases_covered_by_suite = [], set([])
    while True:
        if len(cases_covered_by_suite) == len(cases_spec): break

        test_values = generate_values(parameters)
        test_values.update({
            "integer": dg.integer,
            "word": dg.word,
            "max": max,
            "sum": sum
        })
        cases_covered = cases_covered_by_test(test_values, cases_spec)
        old_len_cases_covered_by_suite = len(cases_covered_by_suite)
        cases_covered_by_suite.update(cases_covered)

        if len(cases_covered_by_suite) > old_len_cases_covered_by_suite or include_all_tests:
            testcase = create_testcase(test_values, cases_covered, input_template, output_template)
            test_suite.append(testcase)

        dg.reset_values()

    return test_suite


def generate_values(parameters):
    """Create test values from a give list of parameters, containing names and
    specifications. Each parameter consists of a map with a single item. The
    item key is taken as the value name and the item value is assumed to be the
    value specification, written as a python expression.

    Returns a map containing the value name mapped to the actual value
    calculated by evaluating the specification.

    CAUTION: eval() is used to evaluate each value spec.
    """
    values = {}
    for value in parameters:
        val_name, val_spec = value.items()[0]
        value = eval(str(val_spec))
        values[val_name] = value

    return values


def cases_covered_by_test(test_values, cases_spec):
    """
    Calculate the cases covered by a test case based on test_values.

    CAUTION: eval() is used to evaluate each case spe.
    """
    cases_covered = []
    for case_name, case_spec in cases_spec.items():
        if eval(str(case_spec), test_values):
            # … test_values validate this case condition
            cases_covered.append(case_name)

    return cases_covered


def create_testcase(test_values, cases_covered, input_template, output_template):
    """
    Create an object (a map) containing the properties of a test case for tst.
    It also includes the list of cases covered as well as the sha1 of the input
    of test case. This can be considered as unique identifier of the test case.
    """
    input_text = input_template.render(test_values)
    input_sha1 = hashlib.sha1(input_text).hexdigest()
    
    return {
        "input": input_text,
        "output": output_template.render(test_values),
        "cases": cases_covered,
        "sha1": input_sha1
    }


def main():
    if not os.path.exists("specs.yaml"):
        tst.cprint(tst.LRED, "no specs.yaml found")
        sys.exit()

    if os.path.exists("tst.json"):
        with codecs.open("tst.json", mode='r', encoding='utf-8') as f:
            tst_json = json.load(f)
    else:
        tst_json = {"tests": []}

    # read specification
    speclist = yaml.load(open("specs.yaml").read())

    # add checksum to each existing test
    tests = tst_json["tests"]
    for test in tests:
        test['sha1'] = test.get('sha1') or hashlib.sha1(test['input']).hexdigest()

    # create tests for each specification element
    for spec in speclist:
        new_tests = create_test_suite(spec, include_all_tests=False)
        tst.cprint(tst.LGREEN, "%d new tests created" % len(new_tests))
        
        # discard duplicated tests
        new_checksums = {test['sha1'] for test in new_tests}
        num_repeated = 0
        for i in range(len(tests) - 1, -1, -1):
            if tests[i]['sha1'] in new_checksums:
                tests.pop(i)
                num_repeated += 1

        tests.extend(new_tests)

    # write tests in tst.json file
    with codecs.open("tst.json", mode='w', encoding='utf-8') as f:
        f.write(json.dumps(tst_json,
            indent=2,
            separators=(',', ': '),
            ensure_ascii=False
        ))

    num_added = len(new_tests) - num_repeated
    tst.cprint(tst.LGREEN, "%d tests added (%d discarded as repeated)" % (num_added, num_repeated))


if __name__ == '__main__':
    main()
