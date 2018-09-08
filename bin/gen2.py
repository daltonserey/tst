# coding: utf-8
import sys
import yaml
import random as random
import json
import hashlib

from jinja2 import Environment, FileSystemLoader, Template
from datagen import word, integer, reset_values

# create jinja environment and read template
env = Environment(loader=FileSystemLoader('.', encoding='utf-8'), keep_trailing_newline=True)
template = env.get_template('template.yaml')

# read tests specification list
speclist = yaml.load(open("specs.yaml").read())

include_all = False

# process each spec item
tests = []
for spec in speclist:
    # read values and cases from spec
    values = spec.get('values', [])
    cases = spec['cases']
    input_template = Template(spec['input_template'], keep_trailing_newline=True)
    output_template = Template(spec.get('output_template', ''), keep_trailing_newline=True)

    covered_by_all_tests = set([])
    while len(covered_by_all_tests) != len(cases):

        old_number = len(covered_by_all_tests)

        # calculate test values
        this_test_values = {}
        for value in values:
            val_name, val_spec = value.items()[0]
            value = eval(str(val_spec))
            globals()[val_name] = value
            this_test_values[val_name] = value

        this_test_values.update({
            "integer": integer,
            "max": max,
            "sum": sum
        })

        # update coverage
        covered_by_this_test = []
        for case_name, case_spec in cases.items():
            if eval(str(case_spec), this_test_values):
                covered_by_this_test.append("%s" % case_name)
                covered_by_all_tests.add(case_name)

        if len(covered_by_all_tests) > old_number or include_all:
            input_text = input_template.render(this_test_values)
            input_sha1 = hashlib.sha1(input_text).hexdigest()
            tests.append({
                "input": input_text,
                "output": output_template.render(this_test_values),
                "cases": covered_by_this_test,
                "sha1": input_sha1
            })

        reset_values()

print json.dumps({
    "tests": tests,
    },
    indent=2,
    separators=(',', ': '),
    ensure_ascii=False
).encode('utf-8')
