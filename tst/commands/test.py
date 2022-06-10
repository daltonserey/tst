from builtins import str
import os
import re
import sys
import json
import shlex
import signal
import string
import unicodedata
import argparse
import logging
import itertools
import queue
import threading
import time
from pathlib import Path
from fnmatch import fnmatch
from fnmatch import filter as fnfilter

from tst.jsonfile import JsonFile
import tst
from tst.utils import _assert
from tst.utils import to_unicode
from tst.utils import cprint
from tst.colors import *

from subprocess import Popen, PIPE, CalledProcessError, TimeoutExpired


PYTHON = 'python3'
if sys.version_info < (3,6):
    sys.stderr.write('tst.py: requires python 3.6 or later\n')
    sys.exit(1)

TIMEOUT_DEFAULT = 2

REDIRECTED = os.fstat(0) != os.fstat(1)

STATUS_CODE = {
    # TST test codes
    'Error': 'e',
    'Timeout': 't',
    'Success': '.',
    'MissingTokens': '%',
    'Fail': 'F',
    'ScriptTestError': '!',
    'NoInterpreterError': 'X',
    'FilenameMismatch': '_',

    # Python ERROR codes
    'AttributeError': 'a',
    'SyntaxError': 's',
    'EOFError': 'o',
    'ZeroDivisionError': 'z',
    'IndentationError': 'i',
    'IndexError': 'x',
    'ValueError': 'v',
    'TypeError': 'y',
    'NameError': 'n',
    '[Errno 2]': '?'
}


class CutTimeOut(Exception): pass


def alarm_handler(_1, _2):
    raise CutTimeOut


signal.signal(signal.SIGALRM, alarm_handler)


def unpack_results(run_method):

    def wrapper(self, *args, **kwargs):
        run_method(self, *args, **kwargs)

        if self.testcase.type == 'io':
            self.result['summary'] = STATUS_CODE[self.result['status']]

        return self.result

    return wrapper


def parse_test_report(data):
    if data and data[0] == '{':
        try:
            # assume it is json
            report = json.loads(data)
            assert 'summary' in report, f'invalid json report: {repr(report)}'
            return report['summary'], report.get('feedback')
        except json.decoder.JSONDecodeError:
            # it is not json
            pass

    parts = data.split('\n', 1)
    summary = parts[0]
    feedback = parts[1] if len(parts) > 1 else None
    return summary, feedback


class TestRun:

    def __init__(self, subject, testcase):
        self.subject = subject
        self.testcase = testcase
        self.result = {}
        self.result['type'] = self.testcase.type
        self.result['fnmatch'] = fnmatch(subject.filename, testcase.fnmatch or "*.py")

    def run(self, timeout=TIMEOUT_DEFAULT):
        if not self.result['fnmatch']:
            self.result['status'] = 'FilenameMismatch'
            self.result['summary'] = STATUS_CODE[self.result['status']]
            return self.result

        if self.testcase.type == 'io':
            return self.run_iotest(timeout)

        elif self.testcase.type == 'script':
            return self.run_script(timeout)

        else:
            _assert(False, 'unknown test type')

    @unpack_results
    def run_script(self, timeout=TIMEOUT_DEFAULT):
        if "{}" in self.testcase.script:
            cmd_str = self.testcase.script.format(self.subject.filename)
        else:
            cmd_str = self.testcase.script
        cmd_str = re.sub(r'\bpython\b', 'python3', cmd_str)
        command = shlex.split(cmd_str)

        self.result['command'] = cmd_str
        stdout, stderr = None, None
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        signal.alarm(10 * timeout)
        try:
            stdout, stderr = map(to_unicode, process.communicate(timeout=timeout))
            signal.alarm(0) # reset the alarm
            process.wait()
            assert process.returncode == 0, f"script test error: exit code = {process.returncode}"

            # collect test data
            self.result['exit_status'] = process.returncode
            self.result['stderr'] = stderr # comment out to remove from report
            self.result['stdout'] = stdout # comment out to remove from report

            # collect report from either stderr or stdout
            summary, feedback = parse_test_report(stderr)
            if not summary:
                summary, feedback = parse_test_report(stdout)
            assert not ' ' in summary and summary == summary.strip(), f'invalid summary: {repr(summary)}'
            assert summary, f"script test error: empty summary"
            self.result['summary'] = summary
            self.result['feedback'] = feedback

        except (FileNotFoundError, PermissionError, AssertionError) as e:
            # the test script command itself failed (or it was not found)
            self.result['status'] = 'ScriptTestError'
            self.result['summary'] = '!'
            self.result['error'] = f'{e}'
            self.result['stderr'] = stderr if stderr else None
            self.result['stdout'] = stdout if stdout else None
            log.warning(f'test script error: CMD=`{cmd_str}` ERROR={e.__class__.__name__} MSG=`{e}`')
            return self.result

        except (CutTimeOut, TimeoutExpired) as e:
            # test script running too long: possibly a loop in the subject
            process.terminate()
            self.result['status'] = 'Timeout'
            self.result['summary'] = 't'
            return self.result

        self.result['summary'] = summary
        if summary == len(summary) * '.':
            self.result['status'] = 'Success'
        else:
            self.result['status'] = 'Fail'

        return self.result

    @unpack_results
    def run_iotest(self, timeout=TIMEOUT_DEFAULT):

        # define command
        config = tst.get_config()
        if config.get('run'):
            # use run option
            run = config['run']
            extensions = run.keys()
            ext = self.subject.filename.split('.')[-1]
            if ext not in extensions:
                self.result['status'] = 'NoInterpreterError'
                return self.result
            _assert(ext in extensions, "\nfatal: missing command for extension %s" % ext)
            command = config['run'][ext]
            cmd_str = "%s %s" % (command, self.subject.filename)
        else:
            # default is running through python
            cmd_str = '%s %s' % (PYTHON, self.subject.filename)

        command = shlex.split(cmd_str)

        # encode test input data
        if self.testcase.input:
            input_data = self.testcase.input.encode('utf-8')
        else:
            input_data = ''
        self.result['input'] = self.testcase.input
        self.result['output'] = self.testcase.output
        self.result['match'] = self.testcase.match

        # run the test (loop until succeeding)
        while True:
            process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            signal.alarm(10 * timeout)
            try:

                # run subject as external process
                process_data = process.communicate(input=input_data, timeout=timeout)
                stdout, stderr = map(to_unicode, process_data)

                # collect output data
                self.result['stdout'] = stdout # comment out to remove from report
                self.result['stderr'] = stderr # comment out to remove from report

                # reset alarm for future use
                signal.alarm(0)
                process.wait()

                # leave loop
                break

            except (CutTimeOut, TimeoutExpired) as e:
                # timeout... give up
                process.terminate()
                self.result['status'] = 'Timeout'
                return self.result

            except OSError:
                # external error... try running again!
                process.terminate()

        # check for ERROR during execution
        if process.returncode != 0:

            # set generic error status
            self.result['status'] = 'Error'

            # try being more specific for known python errors
            for error_code in STATUS_CODE:
                if error_code in stderr:
                    self.result['status'] = error_code
                    break

            return self.result

        # check for a perfect match
        preprocessed_stdout = preprocess(stdout, self.testcase.ignore)
        if self.testcase.preprocessed_output == preprocessed_stdout:
            self.result['status'] = 'Success'
            return self.result

        # check for partial (regex based) match
        if self.testcase.match:
            stdout_regex = stdout
            if self.testcase.re.match(stdout_regex):
                self.result['status'] = 'Success'
                return self.result

        # or fail...
        self.result['status'] = 'Fail'
        return self.result


class TestSubject:

    def __init__(self, filename):
        self.filename = filename
        self.testruns = []
        self._results = None

    def results(self):
        if not self._results:
            self._results = []
            for tr in self.testruns:
                self._results.append(tr.result)

        return self._results

    def summary(self):
        status_codes = [tr['summary'] for tr in self.results()]
        return ''.join(status_codes)


class TestCase():

    def __init__(self, test, test_suite, level, index):

        # get data from tst.json
        self.input = test.get('input', '')
        self.output = test.get('output')
        self.level = level
        self.fnmatch = test.get('fnmatch')
        self.test_suite = test_suite
        self.index = index

        # set match
        if 'match' in test:
            _assert(self.output is None, "cannot set match and output")
            self.match = test['match']
            _assert(isinstance(self.match, str), "match must be a string")
        else:
            self.match = None

        if 'tokens' in test:
            _assert(self.output is None, "cannot set output and tokens")
            _assert(self.match is None, "cannot set match and tokens")
            if type(test["tokens"]) is str:
                tokens = test["tokens"].split()
            else:
                tokens = test["tokens"]
            _assert(all(type(e) is str for e in tokens), "tokens must be a sequence of strings"),
            self.match = ".*\\b" + "\\b.*\\b".join([re.escape(tk) for tk in tokens]) + "\\b.*"

        if 'tokens-regex' in test:
            _assert(self.output is None, "cannot set output and tokens-regex")
            _assert(self.match is None, "cannot set match and tokens-regex")
            _assert(all(type(e) is str for e in test["tokens-regex"]), "tokens-regex must be a sequence of strings"),
            self.match = ".*" + ".*".join(test["tokens-regex"]) + ".*"

        self.ignore = test.get('ignore', [])
        self.script = test.get('script')
        self.type = test.get('type') or ('script' if self.script else 'io')
        if self.type == 'script':
            _assert(self.script, "script tests must have a script")
            _assert(not self.input and not self.output, "script tests cannot have input/output")
            _assert(not self.match, "script tests cannot have tokens/match")

        # convert ignore to a list of strings, if necessary
        if isinstance(self.ignore, str):
            self.ignore = self.ignore.split()

        # compile the regex object
        if self.match and 'case' in self.ignore:
            self.re = re.compile(self.match, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        elif self.match and 'case' not in self.ignore:
            self.re = re.compile(self.match, re.MULTILINE | re.DOTALL)
        else:
            self.re = None

        # set up preprocessed output
        self.preprocessed_output = preprocess(self.output, self.ignore)


def preprocess(text, operator_names):
    if text is None: return None

    # add whites if punctuation is used
    if 'punctuation' in operator_names and 'whites' not in operator_names:
        operator_names = operator_names + ['whites']

    # expand if all is requested
    if operator_names == ['all']:
        operator_names = OPERATOR.keys()

    _assert(all(name in OPERATOR for name in operator_names), "unknown operator in ignore")

    # sort to assure 'whites' is last
    operators = [OPERATOR[name] for name in sorted(operator_names)]

    # apply operators to text
    for op in operators:
        text = op(text)

    return text


def squeeze_whites(text):
    data = [lin.strip().split() for lin in text.splitlines()]
    data = [' '.join(line) for line in data]
    return '\n'.join(data)


def remove_linebreaks(text):
    # TODO: use carefully! it substitutes linebreaks for ' '
    return ' '.join(text.splitlines())


def drop_whites(text):
    # TODO: Use carefully! deletes all whites
    #       string.whitespace = '\t\n\x0b\x0c\r '
    table = dict((ord(char), None) for char in string.whitespace)
    return text.translate(table)


def punctuation_to_white(text):
    # WARNING: preprocess() silently adds 'whites' if punctuation is used
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


def strip_accents(text):
    # text must be a unicode object, not str
    try:
        nkfd_form = unicodedata.normalize('NFKD', text.decode('utf-8'))
        only_ascii = nkfd_form.encode('ASCII', 'ignore')
    except:
        nkfd_form = unicodedata.normalize('NFKD', text)
        only_ascii = nkfd_form.encode('ASCII', 'ignore')

    return only_ascii.decode('utf-8')


OPERATOR = {
    'case': lambda c: c.lower(),
    'accents': strip_accents,
    'extra_whites': squeeze_whites,
    'linebreaks': remove_linebreaks, # not default
    'punctuation': punctuation_to_white, # not default
    'whites': drop_whites, # not default
}


def color(color, text):
    reset = RESET
    if REDIRECTED:
        color = ""
        reset = ""
    return color + text + reset


def get_options_from_cli_and_context(directory, spec):
    DEFAULT_TEST_SOURCES = ["*.yaml", "*.json", "test_*.py", "*_test.py"]

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-V', '--verbose', action="count", default=0, help='more verbose output')
    parser.add_argument('-T', '--timeout', type=int, default=TIMEOUT_DEFAULT, help='stop execution at TIMEOUT seconds')
    parser.add_argument('-t', '--test-sources', nargs="+", default=[], help='read tests from TEST_SOURCES')
    parser.add_argument('-f', '--output-format', type=str, choices=['cli', 'json', 'debug', 'compare'], help='choose report format')
    parser.add_argument('-d', '--diff', action="store_true", default=False, help='shortcut for debug report format')
    parser.add_argument('-c', '--compare', action="store_true", default=False, help='shortcut for color report format')
    parser.add_argument('-P', '--passed', action="store_true", default=False, help='report only passed subjects')
    parser.add_argument('-F', '--failed', action="store_true", default=False, help='report only failed subjects')
    parser.add_argument('filenames', nargs='*', default=[])

    # reuse argparse namespace as the options object
    options = parser.parse_args()

    # process shortcut report options
    _assert(not options.compare or not options.diff, "--compare cannot be used with debug with --diff")
    if options.diff:
        _assert(options.output_format in [None, "debug"], "output-format must be debug with --diff")
        options.output_format = 'debug'

    if options.compare:
        _assert(options.output_format in [None, "compare"], "output-format must be compare with --compare")
        options.output_format = 'compare'

    # set cli as default output_format
    options.output_format = options.output_format or 'cli'

    # identify subjects to be tested/checked
    if not options.filenames:
        # assume all files in directory to possible filenames
        options.filenames = directory

    elif len(options.filenames) == 1 and not Path(options.filenames[0]).exists():
        # if a single filename is not a path: use it as wildcard
        options.filenames = fnfilter(directory, f'*{options.filenames[0]}*')

    # set default test-sources if needed
    if not options.test_sources:
        options.test_sources = []
        for pattern in DEFAULT_TEST_SOURCES:
            options.test_sources.extend(fnfilter(directory, pattern))

    return options


def process_session_tests(testsfile):
    for test in testsfile:
        if 'session' not in test: continue

        input_parts, output_parts = [], []
        for i, part in enumerate(test['session']):
            if type(part) is str:
                if i % 2 == 0:
                    output_parts.append(str(part))
                else:
                    input_part = re.escape(str(part))
                    if input_part[-1] != "\n":
                        input_part += "\n"
                    input_parts.append(input_part)

            if type(part) is dict:
                if "out" in part:
                    output_parts.append(re.escape(str(part["out"])))
                elif "in" in part:
                    input_part = str(part["in"])
                    if input_part[-1] != "\n":
                        input_part += "\n"
                    input_parts.append(input_part)

        test["input"] = "".join(input_parts)

        if test.get("strict"):
            test["output"] = "".join(output_parts)
        else:
            test["match"] = ".*" + ".*".join(output_parts) + ".*"

        del test["session"]


def collect_test_cases(test_sources):
    # collect tests...
    all_test_cases = []

    ## collect yaml/json test suites and tests
    for tspath in test_sources:
        if not tspath.endswith(".json") and not tspath.endswith(".yaml"): continue
        try:
            # collect io test suite
            testsfile = JsonFile(tspath, array2map="tests")
            level = testsfile.get('level', 0)
            process_session_tests(testsfile.data["tests"])
            #pre_process_parts(testsfile.data["tests"])
            test_cases = [TestCase(tc, tspath, level, index) for index, tc in enumerate(testsfile["tests"])]
            all_test_cases.extend(test_cases)

        except tst.jsonfile.CorruptedJsonFile as e:
            cprint(YELLOW, f"invalid json/yaml: {tspath}")

        except KeyError as e:
            pass

    ## if no test has been collected, lets try python script tests
    if not all_test_cases:
        for tspath in test_sources:
            if tspath.endswith(".json") or tspath.endswith(".yaml"): continue

            ## fake script test file
            testsfile = JsonFile(f".{tspath}-autotest.yaml")
            testsfile.data = {'tests': []}
            script_command = None
            if fnmatch(tspath, "*_tests.py"):
                script_command = f'python {tspath} {{}}'
            if fnmatch(tspath, 'test_*.py') or fnmatch(tspath, '*_test.py'):
                script_command = f'pytest {tspath} --tst {{}} --clean'
            if script_command:
                testsfile.data['tests'].append({'type': 'script', 'script': script_command})
                test_cases = [TestCase(tc, tspath, level, index) for index, tc in enumerate(testsfile["tests"])]
                all_test_cases.extend(test_cases)

    return all_test_cases


def run_tests_in_parallel(test_cases, test_suites, subjects, options):
    all_tests_results = []
    verbose = options.verbose
    t0 = time.time()

    def results_reader(q):
        # read queue
        while True:
            test_result = q.get()
            test_result["_test_suite"] = test_result["_testrun"].testcase.test_suite
            test_result["_testcase"] = test_result["_testrun"].testcase
            test_result["subject"] = test_result["_testrun"].subject.filename
            all_tests_results.append(test_result)
            q.task_done()
            verbose > 2 and print(test_result['summary'], flush=True, end='', file=sys.stderr)

    def results_to_map(all_tests_results):
        results = {}

        summaries_sizes = {}
        for ts in test_suites:
            summaries_sizes[ts] = sum(1 for tc in test_cases if tc.test_suite == ts)

        for tr in all_tests_results:
            if not tr['subject'] in results:
                summaries = { ts: ['#'] * summaries_sizes[ts] for ts in test_suites }
                results[tr['subject']] = summaries

            subject_results = results[tr['subject']]
            subject_results[tr['_test_suite']][tr['_testcase'].index] = tr['summary']

        for sub in results.keys():
            for ts in test_suites:
                results[sub][ts] = "".join(summary for summary in results[sub][ts])

        return results

    def print_cli_report(all_tests_results, total_time):
        width = max(len(fn) for fn in subjects)
        results = results_to_map(all_tests_results)
        suppressed = 0
        for fn in results.keys():
            summaries = []
            for ts in test_suites:
                summaries.append(results[fn][ts])
            all_summaries = ' '.join(summaries)
            subject_passed = all(c in '. ' for c in all_summaries)
            if (not options.passed and not options.failed or
                options.passed and subject_passed or
                options.failed and not subject_passed):
                print(f"{fn:{width}s} {all_summaries}", flush=True)
            else:
                suppressed += 1

        print("---")
        print(f"test suites: {' '.join(test_suites)}")
        print(f"number of subjects: {len(subjects) - suppressed} {f'(+{suppressed} omitted)' if suppressed else ''}")
        print(f"number of tests run: {len(all_tests_results)}")
        print(f"time to run all tests: {total_time:.2f}s ({1000 * (total_time / len(all_tests_results)):.1f} ms/test)")

    def print_json_report(all_tests_results):
        results = results_to_map(all_tests_results)
        to_pop = []
        for sub, res in results.items():
            subject_passed = all(c == "." for c in "".join(res.values()))
            if options.passed and not subject_passed:
                to_pop.append(sub)
            elif options.failed and subject_passed:
                to_pop.append(sub)

        for sub in to_pop:
            results.pop(sub)

        print(json.dumps(results))

    def test_runner(testrun, q):
        verbose >= 2 and print(f"* starting test: {testrun.subject.filename} X {testrun.testcase.test_suite}")
        testresult = testrun.run(timeout=options.timeout)
        testresult["_testrun"] = testrun
        q.put(testresult)

    # start reader thread
    verbose and print(f"* starting reader thread", file=sys.stderr)
    q = queue.Queue()
    threading.Thread(target=results_reader, daemon=True, args=(q, )).start()

    # run tests threads
    verbose and print(f"* starting test threads creation", file=sys.stderr)
    threads = []
    subject_threads = []
    last_subject = None
    for subject, testcase in itertools.product(subjects, test_cases):
        #if not fnmatch(subject, testcase.fnmatch or "*.py"): continue
        testrun = TestRun(TestSubject(subject), testcase)
        test_thread = threading.Thread(target=test_runner, args=(testrun, q))
        threads.append(test_thread)
        subject_threads.append(test_thread)
        if subject != last_subject:
            for t in subject_threads: t.start()
            subject_threads = []
        last_subject = subject
    else:
        for t in subject_threads: t.start()

    verbose and print(f"* waiting all {len(threads)} threads finish their jobs", file=sys.stderr)
    for t in threads: t.join()
    verbose and print(f"* threads ended; waiting results reader", file=sys.stderr)
    q.join()
    verbose and print(f"* results collector ended: starting report", file=sys.stderr)
    match options.output_format:
        case 'json':
            print_json_report(all_tests_results)
        case 'debug':
            print("not implemented yet")
        case 'color':
            print("not implemented yet")
        case 'passed':
            print("not implemented yet")
        case 'failed':
            print("not implemented yet")
        case _:
            t1 = time.time()
            print_cli_report(all_tests_results, t1 - t0)


def validate_part_test(test):
    VALID_PARTS_TEST_PROPERTIES = "parts strict delim tokens ignore tokens-regex match".split()

    assert 'parts' in test
    _assert(all(prop in VALID_PARTS_TEST_PROPERTIES for prop in test), "erro 1")
    _assert(all(type(p) is dict for p in test["parts"]), "erro 2")
    _assert(all(len(p.keys()) == 1 for p in test["parts"]), "erro 3")
    _assert(set(next(k for k in p.keys()) for p in test["parts"]).issubset({'in', 'out'}), "erro 4")

    if "tokens" in test:
        _assert("tokens-regex" not in test, "error in test spec")
        _assert("match" not in test, "error in test spec")
        _assert(all(next(k for k in p.keys()) == 'in' for p in test["parts"]), "error in test spec")

    if "tokens-regex" in test:
        _assert("tokens" not in test, "error in test spec")
        _assert("match" not in test, "error in test spec")
        _assert(all(next(k for k in p.keys()) == 'in' for p in test["parts"]), "error in test spec")

    if "match" in test:
        _assert("tokens" not in test, "error in test spec")
        _assert("tokens-regex" not in test, "error in test spec")
        _assert(all(next(k for k in p.keys()) == 'in' for p in test["parts"]))


def create_test_from_parts(test):
    validate_part_test(test)
    new_test = { "_original": test }

    # collect explicit input and output parts
    _in_parts, _out_parts = [], []
    for i, part in enumerate(test['parts']):
        if "out" in part:
            _out_parts.append(part["out"])
        elif "in" in part:
            _in_parts.append(part["in"])

    new_test["input"] = "".join(_in_parts)

    if 'ignore' in test:
        new_test['ignore'] = test['ignore']

    if "tokens" in test:
        new_test["tokens"] = test["tokens"]

    elif "tokens-regex" in test:
        new_test["tokens-regex"] = test["tokens-regex"]

    elif "match" in test:
        new_test["match"] = test["match"]

    elif "strict" in test:
        new_test["match"] = "^" + "".join([re.escape(p) for p in _out_parts]) + "$"

    else:
        delim = test.get("delim") or ".*"
        new_test["match"] = delim + delim.join([re.escape(p) for p in _out_parts]) + delim

    return new_test


def pre_process_parts(testsfile):
    for i in range(len(testsfile)):
        test = testsfile[i]
        if 'parts' not in test: continue
        testsfile[i] = create_test_from_parts(test)


def main():

    # read current directory and specification
    directory = os.listdir()
    spec = tst.read_specification()

    # check spec required files
    for req in spec['require']:
        _assert(any((fnmatch(sub, req) for sub in directory)), "missing required files for this test: %s" % req)

    # identify subjects and test_sources from cli and context
    options = get_options_from_cli_and_context(directory, spec)

    # collect test cases
    test_cases = collect_test_cases(options.test_sources)
    _assert(test_cases, 'no tests collected')
    test_suites = list({tc.test_suite for tc in test_cases})

    # discard test_suites as invalid subjects
    subjects = [sub for sub in options.filenames if sub not in test_suites]
    _assert(subjects, 'no subjects')

    # identify subjects that match test cases
    matching_subjects = set([])
    for sub, tc in itertools.product(subjects, test_cases):
        if fnmatch(sub, tc.fnmatch or "*.py"):
            matching_subjects.add(sub)
    _assert(matching_subjects, 'no matching subjects')

    run_tests_in_parallel(test_cases, test_suites, matching_subjects, options)


log = logging.getLogger('tst-test')
log.setLevel(logging.DEBUG)
handler_file = logging.FileHandler(os.path.expanduser('~/.tst/logs'))
handler_file.setFormatter(logging.Formatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s'))
log.addHandler(handler_file)
log.info(f"CWD={os.getcwd()}")
