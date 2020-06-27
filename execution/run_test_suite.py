#!/usr/bin/env python2.7
import os, subprocess, sys, robot, shutil
import argparse

SCRIPT_DIR = os.getcwd()
ROBOT_DIR = os.path.join(SCRIPT_DIR, '..', '..', '..', '..', '..', 'robot')
DEFAULT_OUTPUT_DIR = os.path.join(ROBOT_DIR, 'output')
SUITES_DIR = os.path.join(ROBOT_DIR, 'implementation', 'testsuites')
PYTHONLIBS_DIR = os.path.join(ROBOT_DIR, '..', 'pythonlibs')
RESOURCE_DIR = os.path.join(ROBOT_DIR, 'implementation', 'resources')
SETTINGS_DIR = os.path.join(ROBOT_DIR, 'execution', 'local', 'settings')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--suite', help='comma separated list of test suites to run (' + print_suites(SUITES_DIR) + ')', required=True)
    parser.add_argument('-e', '--environment', help='environment to run tests against',
                        choices=environments(SETTINGS_DIR), required=True)
    parser.add_argument('-p', '--project', help='JIRA project. If specified test run results will be reported to JIRA',
                        default='')
    parser.add_argument('-k', '--project-key', help='JIRA project key. If specified test run results will be reported to JIRA',
                        default='')
    parser.add_argument('-v', '--project-version', help='JIRA project version', default='')
    parser.add_argument('-c', '--cycle', help='JIRA project cycle', default='')
    parser.add_argument('-i', '--include', help='comma separated list of tags to include', default='')
    parser.add_argument('-x', '--exclude', help='comma separated list of tags to exclude', default='')
    parser.add_argument('-1', help='create issue per test case by default', action='store_true',
                        dest='issue_per_test_case')
    parser.add_argument('-r', '--rerunfailed', help='path to log (output.xml) from previous run', default='')
    parser.add_argument('-l', '--loglevel',
                        help='Threshold level for logging. Available levels: TRACE, DEBUG, INFO (default), WARN, NONE (no logging). Use syntax `LOGLEVEL:DEFAULT` to define the default visible log level in log files. Examples: --loglevel DEBUG, --loglevel DEBUG:INFO',
                        default='')
    parser.add_argument('--no-logs-upload', help='Don not upload logs into Jira', action='store_true')
    parser.add_argument('--force-testcycle',
                        help='forces test cycle set by -c parameter to be applied for all test cases, suite metadata Testcycle will be ignored',
                        action='store_true', dest='force_testcycle')
    parser.add_argument('-d', '--outputdir', help='Output directory', default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--skip-steps', help='Skip test steps updates', action='store_true', dest='skip_steps')
    parser.add_argument('--variables', help='Set variable in the test data', default='')
    parser.add_argument('--listener',
                        help='A class for monitoring test execution. Arguments to the listener class can be given after the name using colon or semicolon as a separator',
                        default='')

    opts = parser.parse_args(sys.argv[1:])

    SUITE = opts.suite
    ENV = opts.environment
    PROJECT = opts.project.replace(' ', '_')
    KEY = opts.project_key.replace(' ', '_')
    VERSION = opts.project_version.replace(' ', '_')
    CYCLE = opts.cycle.replace(' ', '_')
    ISSUE_PER_TEST_CASE = bool(opts.issue_per_test_case)
    TAGS_IN = opts.include
    TAGS_EX = opts.exclude
    LOG = opts.rerunfailed
    LOG_LEVEL = opts.loglevel
    NO_LOGS_UPLOAD = opts.no_logs_upload
    FORCE_TESTCYCLE = bool(opts.force_testcycle)
    SKIP_STEPS = bool(opts.skip_steps)
    VARS = opts.variables
    OUTPUT_DIR = opts.outputdir
    LISTENER = opts.listener

    run(SUITE, ENV, PROJECT, KEY, VERSION, CYCLE, FORCE_TESTCYCLE, TAGS_IN, TAGS_EX, ISSUE_PER_TEST_CASE, LOG, LOG_LEVEL,
        NO_LOGS_UPLOAD, SKIP_STEPS, VARS, OUTPUT_DIR, LISTENER)


def run(suites, env, project='', key='', version='', cycle='', force_testcycle=False, tags_in='', tags_ex='',
        issue_per_test_case=False, log='', log_level='', no_logs_upload=False, skip_steps='', vars = '', output_dir=DEFAULT_OUTPUT_DIR, listener=''):
    print 'running tests using settings: ', env
    # rm -f ROBOT_DIR + '/output/*.*'
    if (os.path.exists(output_dir)):
        shutil.rmtree(output_dir)

    python_executable = 'python'
    if (os.name != 'nt'):
        python_executable += '2.7'

    # generate robomachine tests for this suite
    subprocess.call([python_executable, os.path.join(SCRIPT_DIR, 'generate_robomachine_tests.py'), suites])

    # robot arguments
    arg_list = ['--variablefile', os.path.join(SETTINGS_DIR, env + '.py'),
                '--pythonpath', PYTHONLIBS_DIR + ':' + RESOURCE_DIR + ':' + SETTINGS_DIR,
                '--outputdir', output_dir,
                '--exclude', 'Draft',
                '--nostatusrc',
                '--xunit', 'xunit.xml']

    # if project name is specified test run results will be reported to JIRA using Zephyr
    if project != '':
        arg_list.append('--listener')
        arg_list.append('realtest.zephyr.ZephyrLibrary')

        arg_list.append('--metadata')
        arg_list.append('Project:' + project)

    if key != '':
        arg_list.append('--listener')
        arg_list.append('realtest.zephyr.ZephyrLibrary')

        arg_list.append('--metadata')
        arg_list.append('ProjectKey:' + key)

    if version != '':
        arg_list.append('--metadata')
        arg_list.append('Version:' + version)

    if cycle != '':
        arg_list.append('--metadata')
        arg_list.append('Testcycle:' + cycle)
        if force_testcycle:
            arg_list.append('--metadata')
            arg_list.append('Forced Testcycle:' + cycle)

    if tags_in != '':
        for tag in tags_in.split(','):
            arg_list.append('--include')
            arg_list.append(tag)

    if tags_ex != '':
        for tag in tags_ex.split(','):
            arg_list.append('--exclude')
            arg_list.append(tag)

    if log != '':
        arg_list.append('--rerunfailed')
        arg_list.append(log)

    arg_list.append('--metadata')
    if issue_per_test_case:
        arg_list.append('Issue Per:Test Case')
    else:
        arg_list.append('Issue Per:Test Suite')

    if log_level:
        arg_list.append('--loglevel')
        arg_list.append(log_level)

    if no_logs_upload:
        arg_list.append('--metadata')
        arg_list.append('No Logs Upload:True')

    if skip_steps:
        arg_list.append('--metadata')
        arg_list.append('Skip Steps:True')

    if vars:
        for var in vars.split(' '):
            arg_list.append('--variable')
            arg_list.append(var)

    if listener != '':
        arg_list.append('--listener')
        arg_list.append(listener)

    # specify test suites
    if suites:
        for suite in suites.split(','):
            arg_list.append(os.path.join(SUITES_DIR, suite))

    # run tests
    print "arg_list", arg_list
    robot.run_cli(arg_list)


def print_suites(directory):
    files = os.listdir(directory)
    files = [file for file in files if os.path.isdir(os.path.join(directory, file))]
    return ', '.join(files)


def environments(directory):
    result = []
    for root, dirs, files in os.walk(directory):
        base = os.path.relpath(root, directory)
        base = base if base != '.' else ''
        result += [os.path.join(base, os.path.splitext(file)[0]) for file in files if
                   not base.startswith('_') and not file.startswith('_') and os.path.splitext(file)[1] == '.py']
    return result


if __name__ == '__main__':
    main()
