from builtins import str
import os
import re
import sys
import json
import glob
import shlex
import signal
import string
import unicodedata
import argparse
import difflib
import logging

from tst.jsonfile import JsonFile
import tst
from tst.utils import _assert
from tst.utils import data2json
from tst.utils import to_unicode
from tst.utils import cprint
from tst.utils import indent
from tst.colors import *

from subprocess import Popen, PIPE, CalledProcessError

TIMEOUT_DEFAULT = 2
PYTHON = 'python3'
if sys.version_info < (3,0):
    sys.stderr.write('tst.py: requires python 2.7 or later\n')
    sys.exit(1)

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
}

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

    def __init__(self, subject, testcase, index=None):
        self.subject = subject
        self.testcase = testcase
        self.result = {"index": index}
        self.result['type'] = self.testcase.type

    def run(self, timeout=TIMEOUT_DEFAULT):
        if self.testcase.type == 'io':
            return self.run_iotest()

        elif self.testcase.type == 'script':
            return self.run_script()

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
        try:
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            signal.alarm(timeout)
            stdout, stderr = map(to_unicode, process.communicate())
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
            log.removeHandler(handler_console)
            log.warning(f'test script error: CMD=`{cmd_str}` ERROR={e.__class__.__name__} MSG=`{e}`')
            log.addHandler(handler_console)
            return self.result

        except CutTimeOut:
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
            signal.alarm(timeout)
            try:

                # run subject as external process
                process_data = process.communicate(input=input_data)
                stdout, stderr = map(to_unicode, process_data)

                # collect output data
                self.result['stdout'] = stdout # comment out to remove from report
                self.result['stderr'] = stderr # comment out to remove from report

                # reset alarm for future use
                signal.alarm(0)
                process.wait()

                # leave loop
                break

            except CutTimeOut:
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

        # check for a perfecs match
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
        self._summaries = None

    def results(self):
        if not self._results:
            self._results = []
            for tr in self.testruns:
                self._results.append(tr.result)

        return self._results

    def add_testrun(self, testrun):
        self.testruns.append(testrun)
        self._summaries = None

    def summary(self):
        status_codes = [tr['summary'] for tr in self.results()]
        return ''.join(status_codes)


class TestCase():

    def __init__(self, test):

        # get data from tst.json
        self.input = test.get('input', '')
        self.output = test.get('output')
        self.match = test.get('match')
        self.tokens = test.get('tokens')
        self.ignore = test.get('ignore', [])
        self.script = test.get('script')
        self.type = test.get('type') or ('script' if self.script else 'io')
        if self.type == 'script':
            _assert(self.script, "script tests must have a script")
            _assert(not self.input and not self.output, "script tests cannot have input/output")
            _assert(not self.tokens, "script tests cannot have tokens")

        # check
        if self.output:
            _assert(not self.match and not self.tokens, "cannot be used together: output, match, tokens")
        if self.tokens:
            _assert(not self.match and not self.output, "cannot be used together: output, match, tokens")
        if self.match:
            _assert(not self.output and not self.tokens, "cannot be used together: output, match, tokens")
        _assert(not self.match or isinstance(self.match, str), "match must be a string")
        _assert(self.tokens is None, "tokens based io tests is disabled: requires revision")


        # convert ignore to a list of strings, if necessary
        if isinstance(self.ignore, str):
            self.ignore = self.ignore.split()

        # compile the re object
        if self.match and 'case' in self.ignore:
            self.re = re.compile(self.match, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        elif self.match and 'case' not in self.ignore:
            self.re = re.compile(self.match, re.MULTILINE | re.DOTALL)
        else:
            self.re = None

        # convert tokens to a list of strings, if necessary
        if isinstance(self.tokens, str):
            self.tokens = self.tokens.split()

        # identify tokens within the expected output
        if not self.tokens and self.output and '{{' in self.output:
            p = r'{{(.*?)}}'
            self.tokens = re.findall(p, self.output)
            # remove tokens' markup from expected output
            self.output = re.sub(p, lambda m: m.group(0)[2:-2], self.output)

        # preprocess individual tokens
        if self.tokens:
            for i in range(len(self.tokens)):
                self.tokens[i] = preprocess(self.tokens[i], self.ignore)

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


class CutTimeOut(Exception): pass

class StatusLine:

    def __init__(self):
        if not sys.stdout.isatty():
            self.terminal = False
            return

        self.terminal = True
        self.lastline = ''
        self.stty_size = os.popen('stty size', 'r').read()
        self.columns = int(self.stty_size.split()[1]) - 10

    def set(self, line):
        if not self.terminal:
            return
        GREEN = '\033[92m'
        RESET = '\033[0m'
        line = GREEN + line[:self.columns]+ RESET
        sys.stderr.write('\r%s\r' % ((1+len(self.lastline)) * ' '))
        sys.stderr.write(line)
        sys.stderr.flush()
        self.lastline = line

    def clear(self):
        if not self.terminal:
            return
        sys.stderr.write('\r%s\r' % ((1+len(self.lastline)) * ' '))
        sys.stderr.write('')
        sys.stderr.flush()
        self.lastline = ''


def color(color, text):
    reset = RESET
    if REDIRECTED:
        color = ""
        reset = ""
    return color + text + reset


class Reporter(object):
    VALID_REPORT_STYLES = ['summary', 'debug', 'failed', 'passed', 'json']

    @staticmethod
    def get(style, num_tests=0, options=None):
        """
        Factory method. The style argument specifies the type
        that will be intantiated. If style is None, the base
        class Reporter will be used. If can also be debug,
        failed, passed or json to create either DebugReporter,
        FilterReporter (case of failed or passed) and
        JsonReporter.
        """
        options = options or {}
        _assert(style is None or style in Reporter.VALID_REPORT_STYLES, 'invalid report style: {}'.format(style))
        if style is None or style == 'summary':
            return Reporter(options)

        elif style == 'debug':
            return DebugReporter(max_fails=1, options=options)

        elif style == 'failed':
            fail_filter = lambda s: s.count('.') != len(s)
            return FilterReporter(filtro=fail_filter, options=options)

        elif style == 'passed':
            passed_filter = lambda s: s.count('.') == len(s)
            return FilterReporter(filtro=passed_filter, options=options)

        elif style == 'json':
            return JsonReporter(options=options)

    def __init__(self, options=None):
        self.options = options or {}
        self.num_tests = 0
        self.tests_performed = 0
        self.current_subject = None
        self.testresults = None
        self.testcases = None
        self.subjects = []
        self.status_line = StatusLine()

    def update(self, subject, testcase, testresult):
        if self.current_subject is None:
            hasattr(self, 'before_all') and self.before_all()

        if self.current_subject and subject != self.current_subject:
            # end current_subject report
            self.status_line and self.status_line.clear()
            self.print_report()
            hasattr(self, 'after_file') and self.after_file()
            hasattr(self, 'between_files') and self.between_files()

        if subject != self.current_subject:
            # change to new subject
            hasattr(self, 'before_file') and self.before_file()
            self.current_subject = subject
            self.testresults = []
            self.testcases = []
            self.subjects.append(subject)

        if subject:
            # update data
            self.testresults.append(testresult)
            self.testcases.append(testcase)
            if testresult['type']:
                self.tests_performed += 1
                self._status(self.tests_performed)

    def close(self):
        self.status_line and self.status_line.clear()
        self.print_report()
        hasattr(self, 'after_file') and self.after_file()
        hasattr(self, 'after_all') and self.after_all()

    def _status(self, tests_performed=None):
        if tests_performed is None:
            self.status_line.clear()
            return

        if not self.status_line: return
        self.status_line.set('test %d out of %d' % (tests_performed, self.num_tests))

    def _summaries(self):
        _summaries = []
        for tr in self.testresults:
            _summaries.append(tr['summary'])

        return ''.join(_summaries).strip()

    def print_report(self):
        summary = self._summaries()
        width = min(self.options["max_fn_width"], os.get_terminal_size()[0] - len(summary) - 1)
        line = f'{self.current_subject.filename:{width}.{width}s} {summary}'
        print(line, file=sys.stderr)


class FilterReporter(Reporter):
    def __init__(self, filtro=lambda s: True, options=None):
        options = options or {}
        super(FilterReporter, self).__init__(options)
        self.filtro = filtro

    def print_report(self):
        summary = self._summaries()
        if not self.filtro(re.sub("[ |]", "", summary)): return
        line = '%s%s' % (summary, self.current_subject.filename)
        print(line, file=sys.stderr)


class JsonReporter(Reporter):
    def __init__(self, options=None):
        options = options or {}
        super(JsonReporter, self).__init__(options)
        self._report = {}

    def print_report(self):
        self._report[self.current_subject.filename] = {
            "summary": "".join(self._summaries())
        }

    def after_all(self):
        print(data2json(self._report))


class DebugReporter(Reporter):
    def __init__(self, max_fails=1, options=None):
        options = options or {}
        super(DebugReporter, self).__init__(options)
        self.max_fails = max_fails

    def print_report(self):
        summary = self._summaries()
        line = f'{self.current_subject.filename} {summary}'
        print(line, file=sys.stderr)

        if summary.count('.') == len(summary): return

        for i in range(len(self.testcases)):
            if self.testresults[i]['summary'] == len(self.testresults[i]['summary']) * '.': continue
            testresult = self.testresults[i]
            if testresult['type'] is None: continue

            print(LCYAN + f"\ntest {testresult['index']}: {self.testcases[i].type}" + RESET)
            if testresult['type'] == 'io':
                print(LGREEN + "input: " + RESET + repr(testresult['input']))
                testresult['output'] and print(LGREEN + "output: " + RESET + repr(testresult['output']))
                testresult['match'] and print(LGREEN + "match: " + RESET + testresult['match'])
                print(LGREEN + "stdout: " + RESET + repr(testresult['stdout']))
                status_map = {v:k for k, v in STATUS_CODE.items()}
                status = status_map.get(testresult["summary"])
                print(LGREEN + f"summary:{RESET} {testresult['summary']} ({status})")

                if testresult['output'] and self.options.get('diff'):
                    print(DebugReporter.external_diff(testresult))

                if self.options.get('compare'):
                    print(LGREEN + "compare:" + RESET)
                    print(indent(DebugReporter.internal_diff(testresult)))


            elif testresult['type'] == 'script':
                print(f"{LGREEN}command:{RESET} {testresult['command']}")
                print(LGREEN + f"summary:{RESET} {testresult['summary']}")

                if testresult.get('error'):
                    print(f'{YELLOW}script error:{RESET} {testresult["error"]}')
                if testresult.get('feedback'):
                    cprint(LGREEN, 'script test feedback/report:')
                    print(indent(testresult['feedback']))

            elif testresult['type'] is None:
                pass

            else:
                log.warning('unrecognized test type')


    @staticmethod
    def external_diff(result):
        open('/tmp/input', encoding='utf-8', mode="w").write(result['input'] or '')
        open('/tmp/output', encoding='utf-8', mode="w").write(result['output'] or '')
        open('/tmp/stdout', encoding='utf-8', mode="w").write(result['stdout'] or '')

        try:
            command = tst.get_config().get('diff', 'diff').split() + ["/tmp/stdout", "/tmp/output"]
            process = Popen(command, stdout=PIPE, stderr=PIPE)
            stdout, stderr = map(to_unicode, process.communicate())
            process.wait()
            return stdout.strip()
        except (CalledProcessError, OSError):
            log.error("diff: cannot run external diff command")

    @staticmethod
    def internal_diff(result):
        differ = difflib.Differ()
        diff = differ.compare(result['stdout'].splitlines(), result['output'].splitlines())
        result = ''
        for e in diff:
            if e[0] == '+':
                line = color(LGREEN, "+ ") + color('\033[1;32;100m', e[2:])
            elif e[0] == '-':
                line = color(LRED, "- ") + color('\033[1;31;100m', e[2:])
            else:
                line = color('\033[2m', e)
            result += line + '\n'
        return result


def parse_cli():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-t', '--test-files', type=str, default='*.yaml,*.json', help='read tests from TEST_FILES')
    parser.add_argument('-T', '--timeout', type=int, default=5, help='stop execution at TIMEOUT seconds')

    parser.add_argument('-d', '--diff', action="store_true", default=False, help='print failed testcases and output diff')
    parser.add_argument('-c', '--compare', action="store_true", default=False, help='print colored report of output diff')

    parser.add_argument('-f', '--output-format', type=str, choices=['debug', 'passed', 'failed', 'json'], help='choose output format')
    parser.add_argument('filename', nargs='*', default=[''])
    args = parser.parse_args()

    # identify answer files (files to be tested)
    if len(args.filename) == 1 and os.path.exists(args.filename[0]):
        files2test = [args.filename[0]]
    elif len(args.filename) == 1:
        fn_pattern = '*%s*' % args.filename[0]
        files2test = glob.glob(fn_pattern)
    else:
        files2test = args.filename

    _assert(not (args.diff or args.compare) or args.output_format in [None, 'debug'], 'diff and compare implies debug format')

    # identify test files (files containing tests)
    patterns2scan = args.test_files.split(",") if args.test_files else []
    test_files = []
    for pattern in patterns2scan:
        for filename in glob.glob(pattern):
            if filename not in test_files:
                test_files.append(filename)

    options = {
        "timeout": args.timeout,
        "output-format": args.output_format,
        "diff": args.diff,
        "compare": args.compare,
    }
    return files2test, test_files, options


def main():
    # parse command line
    files2test, test_files, options = parse_cli()

    # read optional specification file
    tstjson = tst.read_specification(verbose=False)

    # check for files required by specification
    for pattern in tstjson.get('require', []):
        _assert(glob.glob(pattern), "Missing required files for this test: %s" % pattern)

    # read tests
    number_of_tests = 0
    test_suites = []
    for filename in test_files:
        try:
            testsfile = JsonFile(filename, array2map="tests")
            number_of_tests += len(testsfile['tests'])
            test_cases = [TestCase(t) for t in testsfile["tests"]]
            test_suites.append((filename, test_cases, testsfile.get('level', 0)))

        except tst.jsonfile.CorruptedJsonFile as e:
            cprint(YELLOW, f"invalid json/yaml: {filename}")

        except KeyError as e:
            pass

    # make sure there are tests
    _assert(number_of_tests, '0 tests found')
    _assert(any(tests for _, tests, _ in test_suites), '0 tests found')
    test_suites.sort(key=lambda ts: ts[2])

    # filter files2test based on extensions and ignore_files
    config = tst.get_config()
    extensions = tstjson.get('extensions') or config['run'].keys() if 'run' in config else ['py']
    ignore_files = tstjson.get('ignore', []) + config.get('ignore', [])
    files2test = [f for f in files2test if any(f.endswith(e) for e in extensions) and f not in ignore_files]
    files2test.sort()
    _assert(files2test, 'No files to test')
    options["max_fn_width"] = max(len(fn) for fn in files2test)

    # read subjects
    subjects = [TestSubject(fn) for fn in files2test]

    _assert(not (options["diff"] or options["compare"]) or len(subjects) == 1, "option --diff/--compare cannot be used with multiple subjects")

    # identify style
    style = options['output-format'] or tst.get_config().get('output-format')
    style = "debug" if options['diff'] or options['compare'] else style

    reporter = Reporter.get(style=style, options=options)
    reporter.num_tests = len(subjects) * number_of_tests
    count, script_errors = 0, []
    for subject in subjects:
        for ts in test_suites:
            testcases = ts[1]
            if not testcases: continue
            for testcase in testcases:
                count += 1
                testrun = TestRun(subject, testcase, index=count)
                testresult = testrun.run(timeout=options['timeout'])
                ('error' in testresult) and script_errors.append(testresult)
                subject.add_testrun(testrun)
                reporter.update(subject, testcase, testresult)
            log.removeHandler(handler_console)
            log.info(f"{subject.filename}: {reporter._summaries()}")
            log.addHandler(handler_console)
            reporter.update(subject, testcase, {"type": None, "summary": " "})

    reporter.close()


class ColorizingStreamHandler(logging.StreamHandler):
    colors_map = {
        logging.DEBUG: LBLUE,
        logging.INFO: LCYAN,
        logging.WARNING: YELLOW,
        logging.ERROR: LRED,
        logging.CRITICAL: CRITICAL
    }

    def emit(self, record):
        try:
            message = self.format(record)
            self.stream.write(message + '\n')
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def format(self, record):
        message = logging.StreamHandler.format(self, record)
        if getattr(self.stream, 'isatty', lambda: None)():
            parts = message.split('\n', 1)
            color = self.colors_map.get(record.levelno, '')
            parts[0] = color + parts[0] + RESET
            message = '\n'.join(parts)
        return message


log = logging.getLogger('tst-test')
log.setLevel(logging.DEBUG)
handler_file = logging.FileHandler(os.path.expanduser('~/.tst/logs'))
handler_file.setFormatter(logging.Formatter('%(asctime)s|%(name)s|%(levelname)s|%(message)s'))
log.addHandler(handler_file)
log.info(f"CWD={os.getcwd()}")
handler_console = ColorizingStreamHandler()
log.addHandler(handler_console)
