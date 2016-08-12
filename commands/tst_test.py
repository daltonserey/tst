#!/usr/bin/env python
# coding: utf-8
# (c) 2011-2014 Dalton Serey, UFCG

from __future__ import print_function
from __future__ import unicode_literals
from collections import OrderedDict, Counter
from difflib import context_diff
import os
import re
import sys
import json
import glob
import getopt
import shlex
import signal
import string
import unicodedata
import itertools
import argparse

import tstlib

# try to import yaml
try:
    import yaml
    we_have_yaml = True

    # reconfigure yaml to load unicode strings instead of str
    from yaml import Loader, SafeLoader
    def construct_yaml_str(self, node):
        return self.construct_scalar(node)

    Loader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
    SafeLoader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)

except ImportError:
  we_have_yaml = False

from datetime import datetime, date
from subprocess import Popen, PIPE, CalledProcessError

TIMEOUT_DEFAULT = 2
PYTHON = "python2.7"
if sys.version_info < (2,7):
    sys.stderr.write("tst.py: requires python 2.7 or later\n")
    sys.exit()

STATUS_CODE = {
  # TST test codes
  "DefaultError": "e",
  "Timeout": "t",
  "Success": ".",
  "NormalizedSuccess": "*",
  "AllTokensSequence": "@",
  "AllTokensMultiset": "&",
  "MissingTokens": "%",
  "Fail": "F",
  "ScriptTestError": "_",

  # Python ERROR codes
  "AttributeError": "a",
  "SyntaxError": "s",
  "EOFError": "o",
  "ZeroDivisionError": "z",
  "IndentationError": "i",
  "IndexError": "x",
  "ValueError": "v",
  "TypeError": "y",
  "NameError": "n",
  "UNKNOWN": "?"
}

def unpack_results(run_method):

    def wrapper(self, *args, **kwargs):
        self.result["test_type"] = self.testcase.type
        self.result["test_name"] = self.testcase.name
        run_method(self, *args, **kwargs)

        if self.testcase.type == "script":
            if self.result['status'] == 'ScriptTestResults':
                self.result['summary'] = self.result['summary']
            else:
                self.result["summary"] = STATUS_CODE[self.result["status"]]

        elif self.testcase.type == "io":
            self.result["summary"] = STATUS_CODE[self.result["status"]]
          
    return wrapper


class TestRunner:

    def __init__(self, testee, testcase):
        self.testee = testee
        self.testcase = testcase
        self.status_code = "&"
        self.result = OrderedDict(status="%", status_code="$")

    def run(self, timeout=TIMEOUT_DEFAULT):
        if self.testcase.type == "io":
            self.run_iotest()

        elif self.testcase.type == "script":
            self.run_script()

        elif self.testcase.type == "analyzer":
            self.run_analyzer()

        else:
            assert False, "unknown test type"


    @unpack_results
    def run_analyzer(self, timeout=TIMEOUT_DEFAULT):
        import analyzer

        analysis_results = to_unicode(analyzer.analyze(self.testee))
        try:
          self.result.update(json.loads(analysis_results))
        except ValueError:
          self.result["status"] = analysis_results


    @unpack_results
    def run_script(self, timeout=TIMEOUT_DEFAULT):
        cmd_str = "%s %s" % (self.testcase.script, self.testee.filename)
        command = shlex.split(cmd_str.encode('utf-8'))
        process = Popen(command, stdout=PIPE, stderr=PIPE) 

        signal.alarm(timeout)
        try:
            stdout, stderr = map(to_unicode, process.communicate())
            signal.alarm(0) # reset the alarm
            process.wait()
        except CutTimeOut: # program didn't stop within expected time
            process.terminate()
            self.result["status"] = "Timeout"
            return

        # collect report from stderr or stdout
        report = stderr or stdout
        if not report:
            self.result['status'] = 'UNKNOWN'
            return
        
        # collect data from report
        self.result["stderr"] = report
        if report[0] == '{':
            # assume it is json
            try:
                data = json.load(report)
                self.result['summary'] = data.get('summary', '')
                self.result['feedback'] = data.get('feedback', [])
            except:
                # either not json, or badly formed json
                pass

        if 'summary' not in self.result:
            # it was not json; assume it is text
            lines = report.splitlines()
            self.result['summary'] = lines[0]
            if len(lines) > 2 and lines[1] == "":
                self.result['feedback'] = "\n".join(lines[2:])


        # collect stdout (supposedly produced by testee)
        self.result["stdout"] = stdout

        # set test result status
        self.result["status"] = "ScriptTestResults"
        if process.returncode or ' ' in self.result['summary']:
            self.result['status'] = 'UNKNOWN'

        return


    @unpack_results
    def run_iotest(self, timeout=TIMEOUT_DEFAULT):

        # define command
        cmd_str = "%s %s" % (PYTHON, self.testee.filename)
        command = shlex.split(cmd_str.encode('utf-8'))

        # encode test input data
        if self.testcase.input:
            input_data = self.testcase.input.encode("utf-8")
        else:
            input_data = ""

        # loop until running the test
        while True:
            process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE) 
            signal.alarm(timeout) 
            try:

                # run testee as external process 
                process_data = process.communicate(input=input_data)
                stdout, stderr = map(to_unicode, process_data)

                # collect output data
                self.result["stdout"] = stdout
                self.result["stderr"] = stderr if stderr else None

                # reset alarm for future use
                signal.alarm(0)
                process.wait()

                # leave loop
                break

            except CutTimeOut:
                # timeout... give up
                process.terminate()
                self.result["status"] = "Timeout"
                return

            except OSError:
                # external error... must run again!
                process.terminate()
      
        # 1. Did an ERROR ocurred during execution?
        if process.returncode != 0:

            # set default error, status and status_code
            self.result["status"] = "DefaultError"

            # try use error code from stderr, if available
            for error_code in STATUS_CODE:
                if error_code in self.result["stderr"]:
                    self.result["status"] = error_code
                    break

            return
      
        # 2. Was it a PERFECTLY SUCCESSFUL run?
        preprocessed_stdout = preprocess(self.result["stdout"],\
                            self.testcase.ignore)
        if self.testcase.preprocessed_output  == preprocessed_stdout:
            self.result["status"] = "Success"
            return


        # 3. Was it a NORMALIZED SUCCESSFUL run?
        normalized_stdout = preprocess(self.result["stdout"], DEFAULT_OPS)
        if self.testcase.normalized_output == normalized_stdout:
            self.result["status"] = "NormalizedSuccess"
            return

        # 4. Doesn't the testcase specify TOKENS?
        if not self.testcase.tokens:
            self.result["status"] = "Fail"
            return

        # set flags to use with methods re.*
        flags = re.DOTALL|re.UNICODE
        if "case" in self.testcase.ignore:
            flags = flags|re.IGNORECASE

        # 5. Does the output have ALL EXPECTED TOKENS IN SEQUENCE?
        regex = "(.*)%s(.*)" % ("(.*)".join(self.testcase.tokens))
        if re.match(regex, preprocessed_stdout, flags=flags):
            self.result["status"] = "AllTokensSequence"
            return

        # 6. Does the output have the TOKENS MULTISET?
        regex = "|".join(self.testcase.tokens)
        found = re.findall(regex, preprocessed_stdout, flags=flags)
        found_ms = Counter(found)                        
        tokens_ms = Counter(self.testcase.tokens)
        if found_ms >= tokens_ms:
            self.result["status"] = "AllTokensMultiset"
            return

        # 7. Does the output have a proper SUBSET OF THE TOKENS?
        if found_ms <= tokens_ms and len(found_ms) > 0:
            self.result["status"] = "MissingTokens"
            return

        # 8. otherwise...
        self.result["status"] = "Fail"
        return
          

class Testee:

    def __init__(self, filename):
        self.filename = filename
        self._io_results = ""
        self.analyzer_results = ""
        self.testruns = []
        self._results = None


    def results(self):
        if not self._results:
          self._results = []
          for tr in self.testruns:
            self._results.append(tr.result)

        return self._results


    def add_testrun(self, testrun):
        self.testruns.append(testrun)


    def feedbacks(self):
        return [tr['feedback'] for tr in self.results() if tr.get('feedback')]


    def summaries(self, join_io=False):
        iosummaries = []
        summaries = []
        for tr in self.results():
            if join_io and tr['test_type'] == 'io':
                iosummaries.append(tr['summary'])
            else:
                summaries.append(tr['summary'])

        if iosummaries:
            summaries.insert(0, "".join(iosummaries))

        return summaries


    def verdict(self):
        return 'success' if all([c == '.' for c in "".join(self.summaries())]) else 'fail'


    def summary(self):
        status_codes = [tr['summary'] for tr in self.results()]
        return "".join(status_codes)



class TestCase():

    def __init__(self, test):

        # get data from tst.json or tst.yaml
        self.name = test.get('name')
        self.type = test.get('type', 'io')
        self.input = test.get('input', "")
        self.output = test.get('output', "")
        self.tokens = test.get('tokens', [])
        self.ignore = test.get('ignore', [])
        self.script = test.get('script')
        self.files = test.get('files')

        # convert tokens to a list of strings, if necessary
        if isinstance(self.tokens, basestring):
            self.tokens = self.tokens.split()

        # convert ignore to a list of strings, if necessary
        if isinstance(self.ignore, basestring):
            self.ignore = self.ignore.split()

        # identify tokens within the expected output
        if not self.tokens and "{{" in self.output:
            p = r"{{(.*?)}}" # r"{{.*?}}|\[\[.*?\]\]"
            self.tokens = re.findall(p, self.output)
            # remove tokens' markup from expected output
            self.output = re.sub(p, lambda m: m.group(0)[2:-2], self.output)

        # preprocess individual tokens
        for i in range(len(self.tokens)):
            self.tokens[i] = preprocess(self.tokens[i], self.ignore)

        # set up preprocessed output
        self.preprocessed_output = preprocess(self.output, self.ignore)

        # set up normalized output
        self.normalized_output = preprocess(self.output, DEFAULT_OPS)

        # setup expression to match tokens (so we do it once for all testees)
        self.tokens_expression = "|".join(self.tokens) if self.tokens else ""



def preprocess(text, operator_names):

    # expand if all is requested
    if operator_names == ['all']:
        operator_names = OPERATOR.keys()

    # sorted to assure 'whites' is last
    operators = [OPERATOR[name] for name in \
                            sorted(operator_names)]

    # apply operators to text
    for op in operators:
        text = op(text)

    return text


def squeeze_whites(text):
    data = [lin.strip().split() for lin in text.splitlines()]
    data = [" ".join(line) for line in data]
    return "\n".join(data)


def remove_linebreaks(text):
    # TODO: use carefully! it substitutes linebreaks for ' '
    return " ".join(text.splitlines())


def drop_whites(text):
    # TODO: Use carefully! deltes all whites
    table = dict((ord(char), None) for char in string.whitespace)
    return text.translate(table)


def punctuation_to_white(text):
    # TODO: Use carefully! it substitutes punctuation for ' '
    # TODO: The specification is wrong!
    #       Punctuation should be changed to spaces? This will
    #       duplicate some whites... Should punctuation be deleted?
    #       This would merge tokens into a single one... Should we
    #       have a mixed behavior? All punctuation surrounded by white
    #       would be deleted and punctuation not surrounded
    # For now, it should be used with whites to work properly.
    table = dict((ord(char), u' ') for char in string.punctuation)
    return text.translate(table)


def squeeze_all_whites(text):
    return " ".join(text.strip().splitlines())


def strip_blanks(text):
    return " ".join(text.split())


def strip_accents(text):
    # text must be a unicode object, not str
    try:
        nkfd_form = unicodedata.normalize('NFKD', unicode(text,'utf-8'))
        only_ascii = nkfd_form.encode('ASCII', 'ignore')
    except:
        nkfd_form = unicodedata.normalize('NFKD', text)
        only_ascii = nkfd_form.encode('ASCII', 'ignore')

    return unicode(only_ascii)


OPERATOR = {
    "case": string.lower,
    "accents": strip_accents,
    "extra_whites": squeeze_whites,
    "linebreaks": remove_linebreaks, # not default
    "punctuation": punctuation_to_white, # not default
    "whites": drop_whites, # not default
}
DEFAULT_OPS = ["case", "accents", "extra_whites"]

class CutTimeOut(Exception):
  pass


def alarm_handler(signum, frame):
    raise CutTimeOut

signal.signal(signal.SIGALRM, alarm_handler)


def to_unicode(obj, encoding='utf-8'):
    assert isinstance(obj, basestring), type(obj)
    if isinstance(obj, unicode):
        return obj

    for encoding in ['utf-8', 'latin1']:
        try:
            obj = unicode(obj, encoding)
            return obj
        except UnicodeDecodeError:
            pass

    assert False, "tst: non-recognized encoding (use utf-8 or latin1)"


def old_to_unicode(obj, encoding='utf-8'):
  assert isinstance(obj, basestring), type(obj)
  if not isinstance(obj, unicode):
    obj = unicode(obj, encoding)

  return obj


def read_tests(tstjson):
    tests = []
    ignore = []

    # read the JSON file
    tests.extend(tstjson.get('tests', []))
    ignore = tstjson.get('ignore')

    # copy default ignore options to testcases without ignore
    if ignore:
        for test in tests:
            if 'ignore' not in test:
                test['ignore'] = ignore

    # instantiate an appropriate TestCase for each test
    testcases = []
    for i in xrange(len(tests)):
        tc = TestCase(tests[i])
        testcases.append(tc)

    return testcases


class StatusLine:

  def __init__(self):
    self.lastline = ""


  def set(self, line):
    GREEN = '\033[92m'
    RESET = '\033[0m'
    line = "tst: testing %s" % line
    line = GREEN + line + RESET
    sys.stderr.write("\r%s\r" % ((1+len(self.lastline)) * ' '))
    sys.stderr.write(line)
    sys.stderr.flush()
    self.lastline = line


  def clear(self):
    sys.stderr.write("\r%s\r" % ((1+len(self.lastline)) * ' '))
    sys.stderr.write("")
    sys.stderr.flush()
    self.lastline = ""


def run_tests(testees, testcases, timeout):

    # prepare status line for user feedback
    status = StatusLine()
    SCREENSIZE = 40

    for testee, testcase in itertools.product(testees, testcases):
      statusline = "%s (%s)..."  % (testee.filename, testcase.name)
      status.set(statusline[:SCREENSIZE])
      testrunner = TestRunner(testee, testcase) # create appropriate runner
      testrunner.run(timeout=timeout)
      testee.add_testrun(testrunner)

    status.clear()


def report_results(testees, verbosity, cwd):

    if verbosity == 0:
      for testee in testees:
        summary = "[%s] %s: %s" % (testee.filename, testee.verdict(), " ".join(testee.summaries(True)))
        print(summary.encode('utf-8'))

    elif verbosity == 1:
      for testee in testees:
        summary = "".join([tr['summary'] for tr in testee.results()])
        summary = "[%s] %s" % (testee.filename, summary)
        print(summary.encode('utf-8'))
        for tr in testee.testruns:
          if tr.status_code != '.':
            if tr.testcase.type == "io" and 'missing_tokens' in tr.result:
              line = "%s|%s (%s '%s')" % (tr.result['summary'], tr.testcase.name, tr.result['status'], tr.result['missing_tokens'])
              print(line.encode('utf-8'))
            else:
              line = "%s|%s (%s)" % (tr.result['summary'], tr.testcase.name, tr.result['status'])
              print(line.encode('utf-8'))

    elif verbosity == 2:
      for testee in testees:
        summary = "".join([tr['summary'] for tr in testee.results()])
        summary = "[%s] %s" % (testee.filename, summary)
        print(summary.encode('utf-8'))
        for tr in testee.testruns:
          if tr.status_code != '.':
            if tr.testcase.type == "io" and 'missing_tokens' in tr.result:
              line = "[%s] %s (%s '%s')" % (tr.result['summary'], tr.testcase.name, tr.result['status'], tr.result['missing_tokens'])
              print(line.encode('utf-8'))
            else:
              line = "[%s] %s (%s)" % (tr.result['summary'], tr.testcase.name, tr.result['status'])
              print(line.encode('utf-8'))
            if tr.testcase.type == "io" and 'stdout' in tr.result and tr.status_code not in STATUS_CODE.values():
              s1 = tr.testcase.output.splitlines(1)
              s2 = tr.result['stdout'].splitlines(1)
              for line in context_diff(s1, s2, fromfile='expected', tofile='observed', n=10):
                sys.stdout.write(line.encode('utf-8'))
              print("***************")

    elif verbosity == 3:

      ## collect all results
      all_results = {}
      for testee in testees:
        result = {}
        result["summary"] = "".join([tr['summary'] for tr in testee.results()])
        feedback = testee.feedbacks()
        if feedback:
            result["feedback"] = feedback
        #result["script_summary_lines"] = [ tr['summary'] for tr in testee.results() if 'summary' in tr]
        #result["script_summary_lines"] = testee.summaries()
        all_results[testee.filename] = result

      print(json.dumps(
          all_results,
          indent=2,
          separators=(',', ': '),
          ensure_ascii=False
      ).encode('utf-8'))

    elif verbosity == 4:

      ## collect all results
      all_results = []
      for testee in testees:
        all_results.append({
          "testee": testee.filename,
          "results": testee.results()
        })

      print(json.dumps(
          all_results,
          indent=2,
          separators=(',', ': '),
          ensure_ascii=False
      ).encode('utf-8'))

    elif verbosity == 5:
      print("%s:" % cwd)
      for testee in testees:
        summary = "".join(testee.summaries())
        summary = "success"  if summary == len(summary) * "." else "fail"
        summary = "    %s: %s" % (testee.filename.split(".py")[0], summary)
        print(summary.encode('utf-8'))

    return


def read_cli():

    from argparse import RawTextHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument("-t", "--timeout", type=int, default=5, help="stop execution at TIMEOUT seconds")
    parser.add_argument("-v", "--verbosity", type=int, default=0, choices=[0,1,2,3,4,5], help="set verbosity level")
    parser.add_argument("filename", nargs="*", default=[""])
    args = parser.parse_args()

    # determine filenames
    if len(args.filename) == 1 and os.path.exists(args.filename[0]):
        filenames = [args.filename[0]]

    elif len(args.filename) == 1:
        fn_pattern = "*%s*.py" % args.filename[0]
        filenames = glob.glob(fn_pattern)

    else:
        filenames = args.filename

    # remove files
    files_to_ignore = ['tst.json']
    filenames = list(set(filenames) - set(files_to_ignore))

    return filenames, args.timeout, args.verbosity


def debug(msg=""):
    cwd = os.path.basename(os.path.normpath(os.getcwd()))
    line = "tst: debug: dir='%s', msg='%s'" % (cwd, msg)
    print(line.encode('utf-8'), file=sys.stderr)


def main():

    # read tstjson
    tstjson = tstlib.read_tstjson(exit=True)

    # read data from cli
    filenames, timeout, verbosity = read_cli()
    filenames = [fn for fn in filenames if fn not in tstjson.get('tst_files', [])]
    cwd = os.path.basename(os.path.normpath(os.getcwd()))
    if not filenames:
        line = "tst: nothing to test in '%s'" % cwd
        print(line.encode('utf-8'), file=sys.stderr)
        sys.exit()
    
    # read testees
    testees = [Testee(fn) for fn in filenames]
    testees.sort(key=lambda t: t.filename)
    
    # read testcases
    testcases = read_tests(tstjson)

    #if tstjson['analyzer']:
    #    asserts_filename = tstjson["asserts"]
    #    if os.path.exists(asserts_filename, os.R_OK):
    #        testcases.append(TestCase(asserts_filename))

    #if os.access("tst-analyzer.py", os.R_OK): # ... and from asserts.py
    #    testcases.append(AnalyzerTestCase("tst-analyzer.py"))

    # exit if there are no tests
    if not testcases:
        line = "tst: no tests found"
        print(line.encode('utf-8'), file=sys.stderr)
        sys.exit()

    # run tests and report results
    run_tests(testees, testcases, timeout)
    report_results(testees, verbosity, cwd)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--one-line-help':
        print("run tests specifiec in tst.json")
        sys.exit()

    main()
