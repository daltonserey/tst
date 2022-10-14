import os
import re
import sys
import json
import shlex
import signal
import string
import argparse
import logging
import itertools
import queue
import threading
import time
import difflib
from pathlib import Path
from fnmatch import fnmatch
from fnmatch import filter as fnfilter

from tst.jsonfile import JsonFile
import tst
from tst.utils import _assert
from tst.utils import to_unicode
from tst.utils import cprint
from tst.colors import *

from subprocess import Popen, PIPE, TimeoutExpired


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
    'Fail': 'F',
    'ScriptTestError': '!',
    'NoInterpreterError': '?',
    'FilenameMismatch': '-',

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
    '[Errno 2]': '2'
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
        fnmatch_options = testcase.fnmatch or ["*.py"]
        self.result['fnmatch'] = any(fnmatch(subject.filename, opt) for opt in fnmatch_options)

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
            self.result['summary'] = STATUS_CODE[self.result['status']]
            self.result['error'] = f'{e}'
            self.result['stderr'] = stderr if stderr else None
            self.result['stdout'] = stdout if stdout else None
            log.warning(f'test script error: CMD=`{cmd_str}` ERROR={e.__class__.__name__} MSG=`{e}`')
            return self.result

        except (CutTimeOut, TimeoutExpired) as e:
            # test script running too long: possibly a loop in the subject
            process.terminate()
            self.result['status'] = 'Timeout'
            self.result['summary'] = STATUS_CODE[self.result['status']]
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
            extensions = config['run'].keys()
            suffix = Path(self.subject.filename).suffix[1:]
            if suffix not in extensions:
                self.result['status'] = 'NoInterpreterError'
                return self.result
            _assert(suffix in extensions, "\nfatal: missing command for extension %s" % suffix)
            command = config['run'][suffix]
            cmd_str = f'{command} "{self.subject.filename}"'
        else:
            # default is running through python
            cmd_str = f'{PYTHON} "{self.subject.filename}"'

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
        if self.testcase.output == stdout:
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

    IO_TEST_PROPS = ['input', 'output', 'parts', 'tokens', 'tokens-regex', 'match']
    SCRIPT_TEST_PROPS = ['script', 'command']

    def _assert_script_spec_validity(self, spec):
        pass

    def _assert_io_spec_validity(self, spec):
        EXCLUSIVE = ['output', 'parts', 'tokens', 'match', 'tokens-regex']
        num = sum(1 for p in EXCLUSIVE if p in spec)
        _assert(num > 0, f"invalid io test (no output specified): {self.id}")
        _assert(num == 1, f"invalid io test (mixed output spec): {self.id}")

    def _guess_type(self, spec):
        test_type = []
        if any(prop in spec for prop in TestCase.IO_TEST_PROPS):
            test_type.append('io')

        if any(prop in spec for prop in TestCase.SCRIPT_TEST_PROPS):
            test_type.append('script')

        _assert(len(test_type) == 1, f"invalid test (unrecognized test type): {self.id}")
        return test_type[0]

    def _preprocess_parts(self, spec):
        in_parts, out_parts = [], []
        for part in spec['parts']:
            _assert(type(part) is dict, f"invalid io test (part is not an object): {self.id}")
            _assert(len(part) == 1, f"invalid io test (part has wrong length): {self.id}")
            if "out" in part:
                out_parts.append(re.escape(str(part["out"])))

            elif "re" in part:
                out_parts.append(str(part["re"]))

            elif "tok" in part:
                out_parts.append(r"\b" + str(part["tok"]) + r"\b")

            elif "in" in part:
                input_part = str(part["in"])
                in_parts.append(input_part)

            elif "lin" in part:
                input_part = str(part["lin"])
                input_part += "\n"
                in_parts.append(input_part)

            else:
                _assert(False, f"invalid io test (invalid part): {self.id}")

        input_value = "".join(in_parts)
        if 'strict-output' in spec.get('options', []):
            output_value = "".join(out_parts)
            match_value = None
        else:
            output_value = None
            match_value = ".*" + ".*".join(out_parts) + ".*"

        return input_value, output_value, match_value

    def _preprocess_tokens(self, spec):
        tokens = spec["tokens"] if type(spec["tokens"]) is list else spec["tokens"].split()
        _assert(all(type(tk) is str for tk in tokens), f"invalid io test (tokens must be strings): {self.id}"),
        match_value = ".*\\b" + "\\b.*\\b".join([re.escape(tk) for tk in tokens]) + "\\b.*"
        return match_value


    def __init__(self, spec, test_suite, level, index):
        # identify test type and check validity
        self.id = f"{test_suite}::{index + 1}"
        self.test_suite = test_suite
        config = tst.get_config()
        self.fnmatch = spec.get('fnmatch') or [f"*.{k}" for k in config.get('run', {}).keys()]
        self.level = level
        self.index = index

        self.type = spec.get('type') or self._guess_type(spec)
        #match self.type:
        if True:
            #case 'script':
            if self.type == 'script':
                self._assert_script_spec_validity(spec)
                self.script = spec.get('script') or spec.get('command')

            #case 'io':
            elif self.type == 'io':
                self._assert_io_spec_validity(spec)
                self.ignore = spec.get('ignore', [])
                if isinstance(self.ignore, str):
                    self.ignore = self.ignore.split()

                if 'output' in spec:
                    _assert(type(spec['output']) in [str, float, int], f"invalid io test (output must be string): {self.id}")
                    self.input = str(spec.get('input', ''))
                    self.output = str(spec['output'])
                    self.match = None

                elif 'match' in spec:
                    _assert(type(spec['match']) is str, f"invalid io test (match must be string): {self.id}")
                    self.input = str(spec.get('input', ''))
                    self.output = None
                    self.match = str(spec['match'])

                elif 'parts' in spec:
                    parts_as_regex = spec.get('match', False)
                    _assert(type(parts_as_regex) is bool, f"invalid io test (match isn't boolean): {self.id}")
                    self.input, self.output, self.match = self._preprocess_parts(spec)

                elif 'tokens' in spec:
                    _assert('match' not in spec, f"invalid io test (tokens and match are incompatible): {self.id}")
                    self.input = str(spec.get('input', ''))
                    self.output = None
                    self.match = self._preprocess_tokens(spec)

                else:
                    assert False, "oops! critical error"

                if self.match:
                    assert not self.output, "invariant violation"
                    options = re.MULTILINE | re.DOTALL
                    if 'case' in self.ignore:
                        options = re.IGNORECASE | options
                    self.re = re.compile(self.match, options)


def get_options_from_cli_and_context(directory):
    DEFAULT_TEST_SOURCES = ["*.yaml", "*.json", "test_*.py", "*_test.py"]

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-V', '--verbose', action="count", default=0, help='more verbose output')
    parser.add_argument('-q', '--quiet', action="store_true", default=False, help='suppress non-essential output')
    parser.add_argument('-T', '--timeout', type=int, default=TIMEOUT_DEFAULT, help='stop execution at TIMEOUT seconds')
    parser.add_argument('-t', '--test-sources', nargs="+", default=[], help='read tests from TEST_SOURCES')
    parser.add_argument('-f', '--output-format', type=str, choices=['default', 'json'], help='choose report format')
    parser.add_argument('-d', '--diff', action="store_true", default=False, help='print diff output for failed io tests')
    parser.add_argument('-c', '--compare', action="store_true", default=False, help='shortcut for compare report format')
    parser.add_argument('-P', '--passed', action="store_true", default=False, help='suppress subjects that fail any test')
    parser.add_argument('-F', '--failed', action="store_true", default=False, help='suppress subjects that pass all tests')
    parser.add_argument('filenames', nargs='*', default=[])

    # reuse argparse namespace as the options object
    options = parser.parse_args()

    if options.compare:
        _assert(options.output_format in [None, "compare"], "output-format must be compare with --compare")
        options.output_format = 'compare'

    # set default as default output_format
    options.output_format = options.output_format or 'default'

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


def collect_test_cases(test_sources):
    # collect tests...
    all_test_cases = []

    ## collect yaml/json test suites and tests
    for tspath in test_sources:
        if all(not fnmatch(tspath, wc) for wc in ["*.json", "*.yaml"]): continue
        try:
            # collect io test suite
            testsfile = JsonFile(tspath, array2map="tests")
            level = testsfile.get('level', 0)
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
            if fnmatch(tspath, 'test_*.py') or fnmatch(tspath, '*_test.py') or fnmatch(tspath, '*/test_*.py'):
                script_command = f'pytest {tspath} --tst {{}} --clean'
            if script_command:
                testsfile.data['tests'].append({'type': 'script', 'script': script_command})
                test_cases = [TestCase(tc, tspath, 0, index) for index, tc in enumerate(testsfile["tests"])]
                all_test_cases.extend(test_cases)

    return all_test_cases


def run_tests_in_parallel(test_cases, test_suites, subjects, options):
    def results_reader(q):
        # read queue
        while True:
            test_result = q.get()
            test_result["_test_suite"] = test_result["_testrun"].testcase.test_suite
            test_result["_testcase"] = test_result["_testrun"].testcase
            test_result["subject"] = test_result["_testrun"].subject.filename
            all_tests_results.append(test_result)
            q.task_done()
            options.verbose > 2 and print(test_result['summary'], flush=True, end='', file=sys.stderr)

    def test_runner(testrun, q):
        options.verbose >= 2 and print(f"** starting test: {testrun.subject.filename} X {testrun.testcase.test_suite}")
        testresult = testrun.run(timeout=options.timeout)
        testresult["_testrun"] = testrun
        q.put(testresult)

    def ui(q):
        time.sleep(1)
        number_test_runs = len(subjects) * len(test_cases)
        done = len(all_tests_results)
        if done > number_test_runs / 2:
            return

        options.verbose >= 0 and print(f"* {number_test_runs} tests threads started (this might take some time)", file=sys.stderr)
        while True:
            done = len(all_tests_results)
            togo = number_test_runs - len(all_tests_results)
            options.verbose and print(f"* {togo} threads still running", file=sys.stderr, flush=True)
            time.sleep(3)

    # main run_tests_in_parallel
    all_tests_results = []
    t0 = time.time()

    # start reader thread
    options.verbose and print(f"* starting results reader thread", file=sys.stderr)
    q = queue.Queue()
    threading.Thread(target=results_reader, daemon=True, args=(q, )).start()
    options.quiet or threading.Thread(target=ui, daemon=True, args=(q, )).start()

    # run tests threads
    options.verbose and print(f"* starting test threads", file=sys.stderr)
    threads = []
    subject_threads = []
    last_subject = None
    for subject, testcase in itertools.product(subjects, test_cases):
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

    for t in threads: t.join()
    options.verbose and print(f"* all test threads finished", file=sys.stderr)
    q.join()
    options.verbose and print(f"* results reader thread finished", file=sys.stderr)

    return all_tests_results


# begin: module reports
def results_to_map(all_tests_results, test_suites, test_cases):
    results = {}

    summaries_sizes = {}
    for ts in test_suites:
        summaries_sizes[ts] = sum(1 for tc in test_cases if tc.test_suite == ts)

    for tr in all_tests_results:
        if not tr['subject'] in results:
            summaries = { ts: ['#'] * summaries_sizes[ts] for ts in test_suites }
            failed = [_tr for _tr in all_tests_results if _tr['summary'] != '.' and _tr['subject'] == tr['subject']]
            summaries['_failed'] = failed
            results[tr['subject']] = summaries

        subject_results = results[tr['subject']]
        subject_results[tr['_test_suite']][tr['_testcase'].index] = tr['summary']

    for sub in results.keys():
        for ts in test_suites:
            results[sub][ts] = "".join(summary for summary in results[sub][ts])

    return results


def print_json_report(results, test_suites, test_cases, options):
    to_pop = []
    for sub, res in results.items():
        failed = res.pop("_failed", None)
        if options.passed and failed:
            to_pop.append(sub)
        elif options.failed and not failed:
            to_pop.append(sub)

    for sub in to_pop:
        results.pop(sub)

    print(json.dumps(results))


def print_cli_report(results, subjects, test_suites, test_cases, options, total_time):
    def indent(text):
        _assert(not text or text[-1] == '\n', "indent deve ser chamada apenas para text terminado em newlines")
        lines = text.splitlines()
        text = "\n".join(["    %s" % l for l in lines])
        return text

    def color(color, text):
        _assert(not text or text[-1] != '\n', "color não deve ser chamada pra string com newline")
        if REDIRECTED:
            return text

        return color + text + RESET

    def internal_diff(result):
        if 'stdout' not in result:
            return None

        differ = difflib.Differ()
        diff = differ.compare(result['stdout'].splitlines(True), result['output'].splitlines(True))
        lines = []
        for e in diff:
            if e[0] == '+':
                line = color(LGREEN, "+ ") + color('\033[1;32;100m', e[2:-1]) + '\n'
            elif e[0] == '-':
                line = color(LRED, "- ") + color('\033[1;31;100m', e[2:-1]) + '\n'
            elif e[0] == '?':
                line = color('\033[2m', e[:-1]) + '\n'
            else:
                line = e
            lines.append(line)
        return "".join(lines)

    width = max(len(fn) for fn in subjects) if subjects else 0
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
            pass
        else:
            suppressed += 1
            continue
        print(f"{fn:{width}s} {all_summaries}")

        # print diff if required
        if options.diff and not subject_passed:
            for tr in results[fn]['_failed']:
                testcase = f"-- {tr['_testcase'].test_suite}::{tr['_testcase'].index + 1}"
                print(color(YELLOW, testcase) + f" ({tr.get('status')})")
                if tr['type'] == 'io' and not tr['match'] and tr.get('summary') not in "et":
                    print(indent(internal_diff(tr)))

    # add meta data to report if required
    if options.quiet: return

    # lines 0 and 1: separator + test suites
    print("---", file=sys.stderr)
    print(f"{len(test_suites)} test suites", end='', file=sys.stderr)
    print(f": {' '.join(test_suites)}" if test_suites else "", file=sys.stderr)

    # line 2: number of test cases and subjects
    print(f"{len(test_cases)} test cases, {len(subjects) - suppressed} subjects", end='', file=sys.stderr)
    print(f" ({suppressed} suppressed)" if suppressed else "", file=sys.stderr)

    # line 3: total tests run + time
    print(f"{len(results)} tests executed in ", end='', file=sys.stderr)
    print(f"{total_time:.2f}s", end='', file=sys.stderr)
    print(f" ({1000 * (total_time / len(results)):.1f} ms/test)" if subjects else " (-.- ms/test)", file=sys.stderr)

# end: module reports


def main():

    # read current directory and specification
    directory = os.listdir()
    spec = tst.read_specification()

    # set options namespace from cli and directory contents
    options = get_options_from_cli_and_context(directory)

    # check spec required files
    for req in spec['require']:
        _assert(any((fnmatch(sub, req) for sub in directory)), "missing required files for this test: %s" % req)

    # collect test suites and test cases
    options.verbose and print("* collecting test cases", file=sys.stderr)
    test_cases = collect_test_cases(options.test_sources)
    test_suites = list({tc.test_suite for tc in test_cases})

    # every file is a potential subject, except for test suites
    possible_subjects = [sub for sub in options.filenames if sub not in test_suites]

    # only files matching some test fnmatch property are valid subjects
    options.verbose and print("* collecting subjects matching test cases fnmatch", file=sys.stderr)
    subjects = set([])
    for sub, tc in itertools.product(possible_subjects, test_cases):
        if sub not in spec['ignore'] and any(fnmatch(sub, fm) for fm in tc.fnmatch):
            subjects.add(sub)

    t0 = time.time()
    all_tests_results = run_tests_in_parallel(test_cases, test_suites, subjects, options)
    results = results_to_map(all_tests_results, test_suites, test_cases)
    t1 = time.time()

    #match options.output_format:
    if True:
        #case 'json':
        if options.output_format == 'json':
            print_json_report(results, test_suites, test_cases, options)
        #case _:
        else:
            print_cli_report(results, subjects, test_suites, test_cases, options, t1 - t0)


log = logging.getLogger('tst-test')
log.setLevel(logging.DEBUG)
handler_file = logging.FileHandler(os.path.expanduser('~/.tst/logs'))
handler_file.setFormatter(logging.Formatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s'))
log.addHandler(handler_file)
log.info(f"CWD={os.getcwd()}")
