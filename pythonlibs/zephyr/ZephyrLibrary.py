""" Implementation of  Robot Framework listener interface. Intended to update Jira Issues and Zephyr for Jira testcases
 during tests execution.

 Zephyr connection settings should be defined as dictionary in Robot Framework variable `${ZEPHYR}` and should contain following keys:
  - `baseURL` - URL to connect to
  - `user` - Jira user name
  - `passwd` - it's password
  - `custom_field_id` - id Zephyr test cases custom field where test case id should be stored
  - `project_key` - test cases project key

 Example definition:

 |ZEPHYR = Dotable.parse({
 |       'baseURL': 'http://0.0.0.0/jira',
 |       'custom_field_id': 13202,
 |       'project_key': 'TP',
 |       'user': 'divya',
 |       'passwd': 'automation'
 |   })



"""
import multiprocessing
import os
import re
from urllib2 import Request, urlopen
from json import dumps, load
from base64 import b64encode
from requests.auth import HTTPBasicAuth
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.String import String
import urllib2
import logging
import logging.config
import sys
from robot import rebot_cli
from requests import post
from . util import escape_string, update_dict_recursively

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

# For debugging purposes.
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
# ch.setFormatter(logging.Formatter('[%(asctime)s] %(message)s'))
# logger.addHandler(ch)


ISSUE_TYPE_NAME = 'Test'
_TEST_CYCLE = 'Testcycle'
_FORCED_TEST_CYCLE = 'Forced Testcycle'
_ISSUE_PER = 'Issue Per'
_ISSUE_PER_TEST_SUITE = 'Test Suite'
_ISSUE_PER_TEST_CASE = 'Test Case'
_ISSUE_PER_DATA_ITEM = 'Data Item'
_NO_LOGS_UPLOAD = 'No Logs Upload'
_SKIP_STEPS = 'Skip Steps'
_METADATA = 'metadata'
_IS_WINDOWS = os.name == 'nt'  # cygwin will produce 'posix' here and this is expected behavior.


class ZephyrError(Exception):
    '''
    Zephyr error. Translates urllib2.HTTPError into specific format for diagnostics.
    '''
    __BASE_MSG = 'Zephyr request failed with code %s: %s\n      %s'
    __LICENSE_MSG = 'Possibly Zephyr licence has expired. Code: %s: %s\n        %s'

    def __init__(self, error):
        if isinstance(error, Exception):
            base_exception = error
            if isinstance(base_exception, urllib2.HTTPError):
                if base_exception.code == 403 or base_exception.code == 405:
                    self.message = self.__LICENSE_MSG % (base_exception.code, base_exception.msg, base_exception.read())
                else:
                    self.message = self.__BASE_MSG % (base_exception.code, base_exception.msg, base_exception.read())
            else:
                self.message = base_exception.message
        else:
            self.message = error

    def __str__(self):
        return self.message


class _MetadataContext(object):
    '''
    Stores metadata in directory-like structure.

    Example:

    Posix:
    ctx.put('/home/user', {'a':1, 'b': 2})
    ctx.put('/home/user/data', {'b': 7, 'c': 3})
    ctx.put('/home/user/data1', {'b': '8', 'd': 4})

    ctx.lookup('/home/user') -> {'a':1, 'b': 2}
    ctx.lookup('/home/user/data') -> {'a':1, 'b': 7, 'c': 3}
    ctx.lookup('/home/user/data1') -> {'a':1, 'b': '8', 'd': 4}

    NT (note: it is case sensitive):
    ctx.put('C:\\Users\\user', {'a':1, 'b': 2})
    ctx.put('C:\\Users\\user', {'b': 7, 'c': 3})
    ctx.put('C:\\Users\\user', {'b': '8', 'd': 4})

    ctx.lookup('C:\\Users\\user') -> {'a':1, 'b': 2}
    ctx.lookup('C:\\Users\\user\\data') -> {'a':1, 'b': 7, 'c': 3}
    ctx.lookup('C:\\Users\\user\\data1') -> {'a':1, 'b': '8', 'd': 4}

    Same as above:
    ctx.put('/C/Users/user', {'a':1, 'b': 2})
    ctx.put('/C/Users/user/data', {'b': 7, 'c': 3})
    ctx.put('/C/Users/user/data1', {'b': '8', 'd': 4})

    ctx.lookup('/C/Users/user') -> {'a':1, 'b': 2}
    ctx.lookup('/C/Users/user/data') -> {'a':1, 'b': 7, 'c': 3}
    ctx.lookup('/C/users/user/data1') -> {'a':1, 'b': '8', 'd': 4}

    Note: only Linux path separator ('/') is supported.
    '''

    def __init__(self, name='/', parent=None):
        '''
        Initializes new context instance.

        :param name: node name
        :param parent: parent node
        '''
        if isinstance(parent, _MetadataContext):
            self.__parent = parent
        else:
            self.__parent = None
        self.__name = name
        self.__lookup = {}
        self.__values = {}

    def lookup(self, p):
        '''
        Looks for context by specified path, then merge all metadata this path possessed.

        :param p: path
        :return: metadata
        '''
        return self.__lookup_ctx(_MetadataContext.__normalize_path(p)).__merge()

    def __lookup_ctx(self, p):
        '''
        Looks recursively for context by specified path.

        :param p: path
        :return: context
        '''
        if p == self.__name:
            return self

        if p in self.__lookup:
            return self.__lookup[p]

        (head, tail) = (p, p)
        if p.startswith('/'):
            (_, head, tail) = p.split('/', 2)
        elif '/' in p:
            (head, tail) = p.split('/', 1)

        if head not in self.__lookup:
            self.__lookup[head] = _MetadataContext(head, self)

        ctx = self.__lookup[head]

        return ctx.__lookup_ctx(tail)

    def put(self, p, v):
        '''
        Puts value into tree by path.

        Raises Exception if v is not instance of dict.

        :param p: path
        :param v: data
        '''
        ctx = self.__lookup_ctx(_MetadataContext.__normalize_path(p))
        if not isinstance(ctx, _MetadataContext):
            raise Exception
        if hasattr(v, 'copy'):
            v = v.copy()
        ctx.__values = v

    def __merge(self):
        '''
        Merges all metadatas (if it is dictionary) in this path. Low level metadata overrides higher level.

        :return: metadata
        '''
        if not isinstance(self.__values, dict):
            return self.__values
        d = {}
        if self.__parent:
            d = self.__parent.__merge()
        d.update(self.__values)
        return d

    @staticmethod
    def __normalize_path(p):
        '''
        Check if path is empty, then returns '/'. If on windows converts all back slashes (\)
        to regular slashes (/), removes colon (:) after drive's name and prepends it with leading slash (/).
        :param p:
        :return: normalized path
        '''
        if not p:
            return '/'
        if _IS_WINDOWS:
            p = p.replace('\\', '/')
            if p[1] == ':':
                p = '/' + p[0] + p[2:]
        return p


class ZephyrLibrary(object):
    ROBOT_LISTENER_API_VERSION = 2
    _CTX = _MetadataContext()

    def __init__(self):
        self.__zephyr = _Zephyr()
        self.__zephyr_tc = _ZephyrTC()
        self.__zephyr_di = _ZephyrDI()
        self.__default_zephyr = self.__zephyr
        self.__delegate = self.__default_zephyr
        self.__no_logs_upload = False

    # robot listener interface
    def start_suite(self, name, attrs):
        """
        Store test suite metadata
        """
        self.__default_zephyr.init_vars()
        metadata = attrs[_METADATA]
        if _ISSUE_PER in metadata:
            issue_per = metadata[_ISSUE_PER]
            if issue_per == _ISSUE_PER_TEST_CASE:
                self.__delegate = self.__zephyr_tc
            elif issue_per == _ISSUE_PER_DATA_ITEM:
                self.__delegate = self.__zephyr_di
            elif issue_per == _ISSUE_PER_TEST_SUITE:
                self.__delegate = self.__zephyr
        # Put metadata into Context.
        ZephyrLibrary.store('Metadata', attrs['source'], metadata)
        self.__delegate.start_suite(name, attrs)
        self.__no_logs_upload = bool(metadata.get(_NO_LOGS_UPLOAD, self.__no_logs_upload))

    def end_suite(self, name, attrs):
        """
        Update Zephyr with test suite execution results
        """
        try:
            self.__delegate.end_suite(name, attrs)
        except urllib2.HTTPError as e:
            raise ZephyrError(e)
        finally:
            metadata = attrs[_METADATA]
            if _ISSUE_PER in metadata:
                self.__delegate = self.__default_zephyr

    def start_keyword(self, name, attrs):
        self.__delegate.start_keyword(name, attrs)

    def end_keyword(self, name, attrs):
        self.__delegate.end_keyword(name, attrs)

    def start_test(self, name, attrs):
        self.__delegate.start_test(name, attrs)

    def end_test(self, name, attrs):
        try:
            self.__delegate.end_test(name, attrs)
        except urllib2.HTTPError as e:
            raise ZephyrError(e)

    def message(self, message):
        self.__delegate.message(message)

    def log_message(self, message):
        self.__delegate.log_message(message)

    def output_file(self, path):
        """
        Asynchronously generate test output and attach it to Zephyr test execution log
        """
        if self.__no_logs_upload:
            return

        zephyrSettings = {'baseURL': _Zephyr.baseURL, '_username': _Zephyr._username, '_password': _Zephyr._password}

        p = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
        for step in self.__delegate.steps:
            p.apply_async(gen_report, (zephyrSettings, path, step))
        p.close()
        p.join()

    @staticmethod
    def lookup(prefix, path):
        return ZephyrLibrary._CTX.lookup(prefix + '$' + path)

    @staticmethod
    def store(prefix, path, value):
        return ZephyrLibrary._CTX.put(prefix + '$' + path, value)


class _Zephyr(object):
    baseURL = ''
    _username = ''
    _password = ''
    _steps = []
    _builtin = BuiltIn()

    def __init__(self):
        self._current_test_name = ''
        self._empty_suite = True
        self._test_results = {}
        self._metadata = {}

    def init_vars(self):
        if not _Zephyr.baseURL:
            _Zephyr.baseURL = self._zephyr_settings.baseURL
        if not _Zephyr._username:
            _Zephyr._username = self._zephyr_settings.user
        if not _Zephyr._password:
            _Zephyr._password = self._zephyr_settings.passwd

    def _process_test_cases(self, project_key, version_id, cycle_id, suite_summary, suite_description,
                            issue_custom_field, issue_custom_field_val, execution_log, execution_status):
        '''
        Process test cases. By default single issue per test suite.

        :param project_key:
        :param version_id:
        :param cycle_id:
        :param suite_summary:
        :param suite_description:
        :param based_on: Jira issue to be linked to test issue
        :param issue_custom_field: custom Jira field name to identify test case issue
        :param issue_custom_field_val: custom Jira field value to identify test case issue
        :param execution_log:
        :param execution_status:
        '''
        based_on = self._metadata.get('Based On', None)
        issue_key = self._metadata.get('Issue', None)
        bugs = []
        for _, t in self._get_test_steps(suite_summary):
            if 'bugs' in t:
                bugs += t['bugs']
        self._process_test_case(project_key, version_id, cycle_id, issue_key, suite_summary, suite_description,
                                based_on, bugs, issue_custom_field, issue_custom_field_val, execution_status,
                                execution_log)

    def _get_test_steps(self, test_case):
        '''
        Provides test case execution steps.

        :return: list of steps
        '''
        return self._test_results.iteritems()

    def _process_test_case(self, project_key, version_id, cycle_id, issue_key, issue_summary,
                           issue_description, based_on, bugs, issue_custom_field, issue_custom_field_val,
                           execution_status, execution_log, test_case_name=None):
        '''
        Process single test case.
        - creates or updates Jira issue
        - updates execution
        - process test steps

        :param project_key:
        :param version_id:
        :param cycle_id:
        :param issue_key:
        :param issue_summary:
        :param issue_description:
        :param based_on:
        :param issue_custom_field:
        :param issue_custom_field_val:
        :param execution_log:
        :param execution_status:
        :return:
        '''
        logger.info('Process test case "%s", metadata: \n%s', issue_summary, self._metadata)
        issue_id, _ = self._process_issue(project_key, issue_key, issue_summary, issue_description, based_on,
                                          bugs, issue_custom_field, issue_custom_field_val)
        project_id = self._get_project_id(project_key)
        execution_id = self._process_execution(project_id, version_id, cycle_id, issue_id, execution_status,
                                               execution_log)

        if bool(self._metadata.get('Attachfile', False)) and '${ATTACHMENT_PATHS}' in self._robot_vars:
            suite_name = self._robot_vars['${SUITE NAME}']
            if suite_name in self._robot_vars['${ATTACHMENT_PATHS}']:
                path_to_file = self._robot_vars['${ATTACHMENT_PATHS}'][suite_name]
                p = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
                p.apply_async(_zephyr_attach_test_execution_log, ({'baseURL': _Zephyr.baseURL, '_username': _Zephyr._username,
                                                                   '_password': _Zephyr._password}, execution_id, path_to_file))
                p.close()
                p.join()
                logger.info('Attachment uploaded: %s', path_to_file)

        if not self.skip_steps:
            self._process_test_steps(issue_id, execution_id, self._get_test_steps(issue_summary))

    def _process_test_suite(self, project_key, suite_summary, suite_description, issue_custom_field,
                            issue_custom_field_val, execution_status, execution_log):
        """
        Executed after test suite execution, performs following actions:
         - Create or update corresponding Zephyr test case
         - If "Based On" metadata exists create or update link to Jira issue.
         - Create Zephyr test cycle
         - Add test step for each `test_result` entry
         - Cleanup existing Zephyr test case execution
         - Store new test execution and it's steps execution
        """
        version_id = self._get_version_id(project_key)
        project_id = self._get_project_id(project_key)

        logger.debug('tear down versionID: %s', version_id)
        logger.debug('tear down projectKey: %s', project_key)
        logger.debug('tear down projectId: %s', project_id)
        logger.debug('tear down issueSummary: %s', suite_summary)
        logger.debug('tear down issueDescription: %s', suite_description)
        logger.debug('tear down issueCustomField: %s', issue_custom_field)
        logger.debug('tear down issueCustomFieldVal: %s', issue_custom_field_val)

        cycle_id = self._process_test_cycle(project_id, version_id, suite_summary)

        self._process_test_cases(project_key, version_id, cycle_id, suite_summary, suite_description,
                                 issue_custom_field, issue_custom_field_val, execution_log, execution_status)

    def _get_project_key(self, default_project_key):
        '''
        Extract project key from metadata or provided default value.

        :param default_project_key:
        :return: project key
        '''
        project_key = default_project_key
        if ('ProjectKey' in self._metadata) and ('Project' not in self._metadata):
            project_key = self._metadata['ProjectKey']

        if 'Project' in self._metadata:
            project_name = self._metadata['Project']
            project_key = ZephyrLibrary.lookup('Project', project_name)
            if not project_key:
                project_key = _get_project_key(self._metadata['Project'])
                ZephyrLibrary.store('Project', project_name, project_key)
        logger.info('Get project key: %s', project_key)
        return project_key

    def _get_version_id(self, project_key):
        '''
        Extracts version from metadata and obtains id for it.

        :param project_key: version project key
        :return: version id or '-1' if metadata missing it
        '''
        version_id = None
        if 'Version' in self._metadata:
            version = self._metadata['Version']
            version_id = ZephyrLibrary.lookup('Version', version)
            if not version_id:
                version_id = _zephyr_get_version_id(project_key, version)
                ZephyrLibrary.store('Version', version, version_id)
        return version_id

    def _get_project_id(self, project_key):
        '''
        Extracts version from metadata and obtains id for it.

        :param project_key: version project key
        :return: version id or '-1' if metadata missing it
        '''
        project_id = ZephyrLibrary.lookup('ProjectKey', project_key)
        if not project_id:
            project_id = _get_project_id(project_key)
            ZephyrLibrary.store('ProjectKey', project_key, project_id)
        return project_id

    def _get_components(self):
        '''
        Extracts components from metadata.

        :return: components
        '''
        components = ''
        if 'Components' in self._metadata:
            components = self._metadata['Components']
        return components

    def _get_test_cycle(self, issue_summary):
        '''
        Extracts test cycle from metadata or tries to parse `issue_summary`.

        :param issue_summary:
        :return: tests cycle name
        '''
        if _TEST_CYCLE in self._metadata:
            cycle_name = self._metadata.get(_FORCED_TEST_CYCLE, self._metadata[_TEST_CYCLE])
        else:
            # cycleName = issueCustomFieldVal[:issueCustomFieldVal.rfind(BuiltIn().get_variable_value('${/}'))]
            dirs = issue_summary.split('.')
            two_segments = [dirs[i] if len(dirs) > i else '' for i in [0, 1]]
            cycle_name = '.'.join(two_segments)
        cycle_name = cycle_name.replace('\\', '/')
        return cycle_name

    def _process_issue(self, project_key, issue_key, issue_summary, issue_description, based_on, bugs,
                       issue_custom_field, issue_custom_field_val):
        '''
        Process Jira issue for test key. If `issue_key` is not specified, tries to find exists issue by
        `issue_custom_field`/`issue_custom_field_val` pair. Otherwise creates new issue.

        - creates or updates Jira issue
        - updates Jira issue links using `based_on` value

        :param project_key:
        :param issue_key:
        :param issue_summary:
        :param issue_description:
        :param based_on:
        :param issue_custom_field:
        :param issue_custom_field_val:
        :return:
        '''
        components = self._get_components()
        issue_key = _zephyr_create_or_update(project_key, issue_key, issue_summary, issue_description,
                                             issue_custom_field, issue_custom_field_val, components)
        issue_id = _get_issue_id(issue_key)

        _jira_update_links(issue_key, based_on, bugs)

        return issue_id, issue_key

    def _process_test_cycle(self, project_id, version_id, issue_summary):
        '''
        Gets test cycle id or creates new if missing.

        :param project_id:
        :param version_id:
        :param issue_summary:
        :return: test cycle id
        '''
        cycle_name = self._get_test_cycle(issue_summary)
        cycle_key = '%s_%s_%s' % (project_id, version_id, cycle_name)
        cycle_id = ZephyrLibrary.lookup('CycleKey', cycle_key)
        if not cycle_id:
            cycle_id = _zephyr_create_test_cycle(project_id, version_id, cycle_name)
            ZephyrLibrary.store('CycleKey', cycle_key, cycle_id)
        return cycle_id

    def _process_execution(self, project_id, version_id, cycle_id, issue_id, execution_status,
                           execution_log):
        '''
        Updates test case execution.

        :param project_id:
        :param version_id:
        :param cycle_id:
        :param issue_id:
        :param execution_status:
        :param execution_log:
        :return: execution id
        '''
        execution_id = _zephyr_execute_test(project_id, version_id, cycle_id, issue_id, execution_status,
                                            execution_log, self.skip_steps)
        return execution_id

    def _process_test_steps(self, issue_id, execution_id, steps):
        '''
        Process test steps. Adds new steps into issue if missing. Puts results into steps.

        :param issue_id:
        :param execution_id:
        :param steps:
        '''
        for k, v in steps:
            if _SKIP_STEPS in v['tags']:
                continue
            v['stepId'] = _zephyr_add_test_step(issue_id, k, v['params'], v['expected'])
            # comment_str = v['comment'] + '\n' + 'log: \n' + v['log'] + '\n' + 'syslog: \n' + v['syslog']
            execution_status = self._get_execution_status(v)
            step_result_id = _zephyr_execute_test_step(v['stepId'], execution_id, execution_status, v['comment'])
            if step_result_id and execution_status in ('PASS', 'FAIL'):
                self.steps.append({'stepResultId': step_result_id, 'longname': v['longname']})

    # robot listener interface
    def start_suite(self, name, attrs):
        pass

    def end_suite(self, name, attrs):
        """
        Update Zephyr with test suite execution results
        """
        try:
            if not self._empty_suite:
                self._metadata = ZephyrLibrary.lookup('Metadata', attrs['source'])
                self._replace_variables_in_metadata()
                logger.debug('End suite "%s", metadata: \n%s', name, self._metadata)
                robot_vars = self._robot_vars
                # here we hardcoded repository structure
                robot_file = String().fetch_from_right(attrs['source'], 'robot{0}implementation{0}testsuites{0}'.format(
                    robot_vars['${/}']))
                robot_zephyr_vars = robot_vars['${ZEPHYR}']
                project_key = self._get_project_key(robot_zephyr_vars.project_key)
                suite_summary = attrs['longname']
                suite_description = attrs['doc']
                custom_field_id = str(robot_zephyr_vars.custom_field_id)
                status = attrs['status']
                message = attrs['statistics']

                self._process_test_suite(project_key, suite_summary, suite_description,
                                         custom_field_id, robot_file,
                                         status, message)
        finally:
            self._empty_suite = True
            self._test_results = {}
            self._metadata = {}

    def start_keyword(self, name, attrs):
        """
        Init `_test_results` map for templated and combinatorial testcases
        """
        if attrs['type'] == 'Keyword':
            if self._current_test_name:
                res = self._test_results[self._current_test_name]
                if (res['template'] and res['template'] == name) or \
                                name == 'Set Machine Variables':  # this is for the combinatorial generated tests
                    res['params'] = ', '.join(attrs['args'])
                    res['template'] = None
                    self._current_test_name = None

    def end_keyword(self, name, attrs):
        pass

    def start_test(self, name, attrs):
        """
        Init `_test_results` map
        """
        self._current_test_name = name
        data = self._process_tags(attrs['tags'])
        res = {
            'template': attrs['template'],
            'expected': attrs['doc'],
            'longname': attrs['longname'],
            'name': name,
            'params': '',
            'comment': '',
            'log': '',
            'syslog': '',
            'status': 'UNEXECUTED',
            'tags': attrs['tags'],
            'doc': attrs['doc'],
            'based_on': data.get('based_on', self._metadata.get('Based On', None)),
            'issue_key': data.get('issue', self._metadata.get('Issue', None)),
            'bugs': data.get('bugs', [])
        }

        self._test_results[name] = res

    def end_test(self, name, attrs):
        """
        Update `test_results`
        """
        self._empty_suite = False
        res = self._test_results[name]
        res['status'] = attrs.get('status', res['status'])
        res['comment'] = attrs.get('message', res['comment'])
        res['tags'] = attrs.get('tags', res['tags'])

        res['expected'] = self._robot_vars.get('${' + self._current_test_name + '_EXPECTED_RESULT}', 'PASS')
        res['params'] = self._robot_vars.get('${' + self._current_test_name + '_TEST_DATA}', '')

        # post process tags
        self._current_test_name = None

    def _replace_variables_in_metadata(self):
        for key, value in self._metadata.iteritems():
            try:
                self._metadata[key] = self._builtin.replace_variables(self._metadata[key])
            except:
                logger.warning("Failed to replace variables in: " + key + ":" + self._metadata[key])

    def _get_execution_status(self, res):
        '''
        Get execution status base on current result status and tags.
        :param res: test case execution result
        :return: status
        '''
        data = self._process_tags(res['tags'])
        ignored = data.get('ignore', False)
        status = res['status']
        if ignored and (res['longname'] in ignored or '*** Test Case ***' in ignored):
            status = 'UNEXECUTED'
        return status

    def _process_tags(self, tags):
        '''
        Extracts 'Based On' and 'Issue' from tags.
        :param tags: list of tags
        :return: dictionary containing 'Based On' and 'Issue' values
        '''
        data = {}

        for tag in tags:
            tag_u = tag.translate(' ').upper()
            if tag_u.startswith('BASEDON:'):
                data['based_on'] = tag.split(':', 1)[1]
            elif tag_u.startswith('ISSUE:'):
                data['issue'] = tag.split(':', 1)[1]
            elif tag_u.startswith('BUG:'):
                if 'bugs' not in data:
                    data['bugs'] = []
                data['bugs'].append(tag.split(':', 1)[1])
            elif tag_u.startswith('IGNORE'):
                if 'ignore' not in data:
                    data['ignore'] = []
                if ':' in tag:
                    data['ignore'].append(tag.split(':', 1)[1])
                else:
                    data['ignore'].append('*** Test Case ***')
            elif tag_u == 'DRAFT':
                if 'ignore' not in data:
                    data['ignore'] = []
                data['ignore'].append('*** Test Case ***')
        return data

    def message(self, message):
        # self.save_log_message(message, 'log')
        pass

    def log_message(self, message):
        # self.save_log_message(message, 'syslog')
        pass

    @property
    def _zephyr_settings(self):
        '''
        Get Zephyr settings from <settings>.py .
        '''
        return self._robot_vars['${ZEPHYR}']

    @property
    def _robot_vars(self):
        '''
        Gets robot variables.
        '''
        # workaround to save inconsistency between robot 2.8 and robot 2.9
        variables = self._builtin.get_variables()
        for name in list(variables):
            if name.startswith('&'):
                variables['$' + name[1:]] = variables.pop(name)
        return variables

    @property
    def steps(self):
        return _Zephyr._steps

    @steps.setter
    def steps(self, steps):
        _Zephyr._steps = steps

    @property
    def skip_steps(self):
        return bool(self._metadata.get(_SKIP_STEPS, False))

class _ZephyrTC(_Zephyr):
    '''
    Unlike ZephyrLibrary ZephyrLibraryTC creates issue per test case instead of per test suite.
    Current implementation also skips updated.
    '''

    _keyword_message = ''

    def __init__(self):
        super(_ZephyrTC, self).__init__()
        self._level = 0
        self._test_steps = {}

    def _process_test_steps(self, issue_id, execution_id, steps):
        '''
        Process test steps. Adds new steps into issue if missing.

        :param issue_id:
        :param execution_id:
        :param steps:
        '''
        for k, v in steps:
            v['stepId'] = _zephyr_add_test_step(issue_id, k, v['params'], v['expected'])
            _zephyr_execute_test_step(v['stepId'], execution_id, self._get_execution_status(v), v['comment'])

    def _process_test_cases(self, project_key, version_id, cycle_id, suite_summary, suite_description,
                            issue_custom_field, issue_custom_field_val, execution_log, execution_status):
        for test_case_key, test_case in self._test_results.iteritems():
            self._process_test_case(project_key, version_id, cycle_id, test_case['issue_key'],
                                    suite_summary + ': ' + test_case_key, test_case['doc'] or suite_description,
                                    test_case['based_on'], test_case['bugs'], issue_custom_field,
                                    issue_custom_field_val + '::' + test_case_key,
                                    self._get_execution_status(test_case), test_case['comment'], test_case['name'])

    def _process_test_case(self, project_key, version_id, cycle_id, issue_key, issue_summary, issue_description,
                           based_on, bugs, issue_custom_field, issue_custom_field_val, execution_status, execution_log,
                           test_case_name=None):
        issue_id, _ = self._process_issue(project_key, issue_key, issue_summary, issue_description, based_on,
                                          bugs, issue_custom_field, issue_custom_field_val)
        project_id = self._get_project_id(project_key)
        execution_id = self._process_execution(project_id, version_id, cycle_id, issue_id, execution_status,
                                               execution_log)
        if execution_status in ('PASS', 'FAIL'):
            if not self.skip_steps:
                self._process_test_steps(issue_id, execution_id, self._get_test_steps(test_case_name))
            self.steps.append({'executionId': execution_id, 'longname': test_case_name})
        logger.info('Test case %s is processed', issue_key)

        if test_case_name in self._test_results and 'attachfile' in self._test_results[test_case_name]['tags'] and '${ATTACHMENT_PATHS}' in self._robot_vars:
            if test_case_name in self._robot_vars['${ATTACHMENT_PATHS}']:
                path_to_file = self._robot_vars['${ATTACHMENT_PATHS}'][test_case_name]
                p = multiprocessing.Pool(multiprocessing.cpu_count() * 2)
                p.apply_async(_zephyr_attach_test_execution_log, ({'baseURL': _Zephyr.baseURL, '_username': _Zephyr._username,
                                                                   '_password': _Zephyr._password}, execution_id, path_to_file))
                p.close()
                p.join()
                logger.info('Attachment uploaded: %s', path_to_file)

    def _get_test_steps(self, test_case):
        '''
        Gets test execution steps.
        :param test_case: test case
        :return: list of tuples (longname, test_step)
        '''
        if test_case not in self._test_steps:
            return []
        return [(step['longname'], step) for step in self._test_steps[test_case]]

    # robot listener interface
    def start_keyword(self, name, attrs):
        self._level += 1

    def end_keyword(self, name, attrs):
        super(_ZephyrTC, self).end_keyword(name, attrs)
        try:
            self.__add_step(name, attrs)
        finally:
            self._level -= 1

    def __add_step(self, name, attrs):
        if (attrs['type'] in
                ('Suite Setup', 'Suite Teardown', 'Test Setup', 'Test Teardown', 'Keyword') and self._level == 1) or \
                (attrs['type'] in ('Test Foritem') and self._level == 2):
            if attrs['type'] in ('Keyword', 'Test Foritem'):
                key = self._current_test_name
            else:
                key = attrs['type']

            if attrs['type'] == 'Test Foritem':
                longname = self._robot_vars.get('${' + self._current_test_name + '_SCENARIO_NAME}')
                expected = self._robot_vars.get('${' + self._current_test_name + '_EXPECTED_RESULT}')
            else:
                longname = name
                expected = 'PASS'

            if not longname:
                logger.info('Can not obtain long name for keyword "%s"', name)
                return
            if self._current_test_name in self._test_results:
                test_step = self._test_results[self._current_test_name].copy()
            else:
                test_step = {
                    'comment': '',
                    'log': '',
                    'syslog': '',
                }
            test_step.update({
                'template': attrs.get('template', ''),
                'expected': expected,
                'longname': longname,
                'name': key,
                'params': ', '.join(attrs['args']),
                'status': attrs['status'],
                'comment': self._keyword_message,
                'tags': self._robot_vars.get('@{TEST_TAGS}', []),
                'doc': attrs['doc'],
            })
            # If we are on Suite Setup stage, there is no self._test_steps[key] is defined yet.
            if key not in self._test_steps:
                self._test_steps[key] = []
            self._test_steps[key].append(test_step)
        elif attrs['type'] == 'Test Teardown' and name == 'util.Report Status Message':
            # Save keyword status message for later use when process the for item
            # 'util.Report Status Message' keyword should be called from test template keyword teardown to enable this
            self._keyword_message = self._robot_vars.get('${KEYWORD_MESSAGE}')

    def start_test(self, name, attrs):
        super(_ZephyrTC, self).start_test(name, attrs)
        self._test_steps[name] = []

    def end_test(self, name, attrs):
        super(_ZephyrTC, self).end_test(name, attrs)
        self._level = 0
        self._test_steps[name] = self._test_steps.pop('Test Setup', []) + self._test_steps[name]
        self._test_steps[name] = self._test_steps.get('Suite Setup', []) + self._test_steps[name]
        self._test_steps[name] += self._test_steps.pop('Test Teardown', [])
        self._test_steps[name] += self._test_steps.get('Suite Teardown', [])

    def end_suite(self, name, attrs):
        super(_ZephyrTC, self).end_suite(name, attrs)
        self._test_steps = {}


class _ZephyrDI(_ZephyrTC):
    def __init__(self):
        super(_ZephyrDI, self).__init__()

    def end_keyword(self, name, attrs):
        """
        Init `_test_results` map
        """
        if attrs['type'] in ('Test Foritem') and self._level == 2:
            key = self._robot_vars.get('${' + self._current_test_name + '_SCENARIO_NAME}')
            issue_key = self._robot_vars.get('${' + self._current_test_name + '_ISSUE_KEY}')
            if not key:
                raise Exception(
                    'Keyword "util.Report As" must be called for "' + _ISSUE_PER + '  ' + _ISSUE_PER_DATA_ITEM + '" reports.')
            _test_result = self._test_results[self._current_test_name].copy()
            _test_result.update({
                'status': attrs['status'],
                'longname': key,
                'comment': '',
                'tags': self._robot_vars.get('@{TEST_TAGS}'),
                'doc': attrs['doc'],
                'issue_key': issue_key
            })
            self._test_results[key] = _test_result

        self._level -= 1

    def start_test(self, name, attrs):
        """
        Init `_test_results` map
        """
        super(_ZephyrDI, self).start_test(name, attrs)

    def end_test(self, name, attrs):
        """
        Update `test_results`
        """
        self._level = 0
        del self._test_results[self._current_test_name]
        self._empty_suite = not (len(self._test_results) > 0)
        self._current_test_name = None


def _jira_get_issue_links(issue_key):
    """
    Returns list of links for Zephyr test by it's `issue_key`
    """
    url = _Zephyr.baseURL + '/rest/api/2/issue/' + issue_key + '?fields=issuelinks'
    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)
    res = []
    for l in resp_json['fields']['issuelinks']:
        if 'outwardIssue' in l and l['type']['name'] == 'Relates':
            res.append({'id': l['id'], 'issueKey': l['outwardIssue']['key']})
    return res


def _jira_delete_link(linked_issue_id):
    """
    Delete Jira issue link with specified `linkId`
    """
    url = _Zephyr.baseURL + '/rest/api/2/issueLink/' + linked_issue_id
    headers = _headers()
    request = Request(url, headers=headers)
    request.get_method = lambda: 'DELETE'
    js_res = urlopen(request)
    load(js_res)


def _jira_update_links(issue_key, based_on_issues_val, bugs):
    """
    Update Zephyr test links using `basedOnIssuesVal` metadata value
    """
    issues = split_metadata_value(based_on_issues_val) + bugs
    if not issues:
        logger.info('No links for issue %s specified. Skip.', issue_key)
        return
    existing_links = _jira_get_issue_links(issue_key)

    for issue in issues:
        if issue not in [link['issueKey'] for link in existing_links]:
            json_data = {
                'type': {
                    'name': 'Relates'
                },
                'inwardIssue': {
                    'key': issue_key
                },
                'outwardIssue': {
                    'key': issue
                }
            }

            url = _Zephyr.baseURL + '/rest/api/2/issueLink/'
            headers = _headers()
            request = Request(url, data=dumps(json_data), headers=headers)
            try:
                js_res = urlopen(request)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    logger.info('"Based on" issue %s was not found.', issue)
                else:
                    logger.error(e.message)
    logger.info('Links for issue %s are updated', issue_key)


def _jira_find_test(project_key, issue_custom_field, issue_custom_field_val):
    """
    Find Zephyr test for project with key `projectKey`, custom field `issueCustomField` and it's value `issueCustomFieldVal`
    """
    search_url = _Zephyr.baseURL + '/rest/api/2/search/?fields=id&jql='
    issue_custom_field_val_esc = escape_string(
        re.sub(r'([+\-&|!\^~*?\'\\])', '\\\\\\1', issue_custom_field_val))
    search_url += urllib2.quote(('issuetype=Test AND cf[' + issue_custom_field + ']~\'' + issue_custom_field_val_esc
                                 + '\' AND project=' + project_key).encode('utf8'), safe='')

    logger.info('Search Jira issue, url: %s', search_url)

    headers = _headers()
    request = Request(search_url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)

    num_found = resp_json['total']

    if num_found > 0:
        issue_key = resp_json['issues'][0]['key']
        logger.debug('Test found. KEY is: %s', issue_key)
        return issue_key

    return None


def _get_project_key(project_name):
    """
    Returns project key for specified `projectName`
    """
    url = _Zephyr.baseURL + '/rest/api/2/project'
    logger.info('Get project name: %s', url)
    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)
    for project in resp_json:
        if project['name'] == project_name:
            return project['key']
    return


def _get_project_id(project_key):
    """
    Returns project id for specified `projectKey`
    """
    url = _Zephyr.baseURL + '/rest/api/2/project/' + project_key
    logger.info('Get project ID: %s', url)
    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)
    return resp_json['id']


def _zephyr_create_or_update(project_key, issue_key, issue_summary, issue_description, issue_custom_field,
                             issue_custom_field_val, components):
    """
    Create or update Jira issue using specified parameters
    """
    issue_custom_field_name = 'customfield_' + issue_custom_field
    issue_custom_field_val = issue_custom_field_val.replace('\\', '/')
    create_test_issue_url = _Zephyr.baseURL + '/rest/api/2/issue/'

    issue_specified = bool(issue_key)
    if not issue_key:
        issue_key = _jira_find_test(project_key, issue_custom_field, issue_custom_field_val)

    if issue_key:
        logger.info('Updating existing Jira Issue Id: %s', issue_key)
        create_test_issue_url += issue_key
        logger.debug('URL is: %s', create_test_issue_url)
        action = 'Updating'
        update = True
    else:
        update = False
        action = 'Creating'

    logger.info(
        'Test JIRA, args: \n\
\taction: %s\n\
\tproject_key: %s\n\
\tissue_summary: %s\n\
\tissue_description: %s\n\
\tissue_custom_field: %s\n\
\tissue_custom_field_val: %s\n',
        action, project_key, issue_summary, issue_description, issue_custom_field,
        issue_custom_field_val)

    components_json = []
    for component in split_metadata_value(components):
        components_json.append({'name': component})

    issue = {
        'fields': {
            'project': {
                'key': project_key
            },
            'components': components_json,
            'issuetype': {
                'name': ISSUE_TYPE_NAME
            },
            issue_custom_field_name: issue_custom_field_val
        }
    }
    # update summary and description only on creation
    if not issue_specified and action=='Creating':
        update_dict_recursively(issue, {
            'fields': {
                'summary': issue_summary,
                'description': issue_description,
            }
        })

    headers = _headers()
    request = Request(create_test_issue_url, data=dumps(issue), headers=headers)

    if update:
        request.get_method = lambda: 'PUT'

    try:
        js_res = urlopen(request)
    except urllib2.HTTPError, ex:
        if ex.code == 400:
            resp = ex.read()
            # In case issue was closed and can not be updated.
            if issue_key and 'You do not have permission to edit issues in this project.' in resp:
                logger.warning('Issue "%s" probably closed and can not be updated.', issue_key)
                return issue_key
            logger.error('Error has occurred while creating/updating issue:  %s', resp)
        raise ex

    if update:
        logger.info('Test issue updated: %s', issue_key)
    else:
        resp_json = load(js_res)
        issue_key = resp_json['key']
        logger.info('Test issue created: %s', issue_key)

    return issue_key


def _zephyr_find_test_cycle(project_id, version_id, name):
    """
    Find Zephyr test cycle id by it's `project_id`, `version_id` and `name`,
    """
    if not version_id:
        version_id = '-1'

    url = _Zephyr.baseURL + '/rest/zapi/latest/cycle?projectId=' + project_id + '&versionId=' + version_id

    logger.info('Get test cycle: %s', url)

    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)

    for k, v in resp_json.iteritems():
        if k != 'recordsCount':
            if v['name'] == name:
                return k
    return None


def _zephyr_create_test_cycle(project_id, version_id, name):
    """
    Create or update Jira issue using specified `project_id`, `versionId` and `name` parameters
    """
    cycle_id = _zephyr_find_test_cycle(project_id, version_id, name)
    if cycle_id:
        logger.debug('Found existing test cycle: %s', cycle_id)
        return cycle_id

    if not version_id:
        version_id = '-1'

    logger.debug('Create test cycle, args: \n\
\tname=%s\n\
\tproject_id=%s\n\
\tname=%s\n\
\tversion_id=%s\n',
                 name,
                 project_id,
                 version_id)

    test_cycle = {
        'name': name,
        'projectId': project_id,
        'versionId': version_id
    }

    headers = _headers()
    url = _Zephyr.baseURL + '/rest/zapi/latest/cycle'
    request = Request(url, data=dumps(test_cycle), headers=headers)
    js_res = urlopen(request)

    resp_json = load(js_res)
    cycle_id = resp_json['id']
    logger.info('Test cycle created. New ID is: %s', cycle_id)

    return cycle_id


def _get_issue_id(issue_key):
    """
    Get Jira test id by `testKey`
    """
    url = _Zephyr.baseURL + '/rest/api/2/issue/' + issue_key
    logger.info('Get test ID: %s', url)
    logger.info('Test Jira issue URL: %s', _Zephyr.baseURL + '/browse/' + issue_key)

    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)
    return resp_json['id']


def _zephyr_find_execution(cycle_id, version_id, issue_id):
    """
    Retrieve Zephyr test execution id by 'testId` and `cycleId`
    """
    if not version_id:
        version_id = '-1'

    url = _Zephyr.baseURL + '/rest/zapi/latest/execution?issueId=' + issue_id
    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)

    executions = resp_json['executions']
    for item in executions:
        if str(item['cycleId']) == cycle_id and str(item['versionId']) == version_id:
            return str(item['id']), str(item['executionStatus'])
    return None, None

def _zephyr_delete_execution(execution_id):
    """
    Cleanup Zephyr test execution by `issue_id` and `cycleId`
    """
    # delete
    if execution_id:
        url = _Zephyr.baseURL + '/rest/zapi/latest/execution/%s' % execution_id
        headers = _headers()
        request = Request(url, headers=headers)
        request.get_method = lambda: 'DELETE'
        js_res = urlopen(request)
        resp_json = load(js_res)
        logger.info('Test execution deleted. ID: %s', execution_id)


def _zephyr_execute_test(project_id, version_id, cycle_id, issue_id, exec_status, exec_log, skip_steps):
    """
    Create Zephyr test execution using specified parameters
    """
    if isinstance(exec_status, basestring):  # pass numeric status as is
        if exec_status == 'PASS':
            exec_status = 1
        elif exec_status == 'FAIL':
            exec_status = 2
        else:
            exec_status = -1

    execution_id, cur_exec_status = _zephyr_find_execution(cycle_id, version_id, issue_id)
    if not skip_steps and execution_id:
        _zephyr_delete_execution(execution_id)
        execution_id = None
        cur_exec_status = -1

    headers = _headers()

    if not execution_id:
        if not version_id:
            version_id = '-1'

        json_data = {
            'issueId': issue_id,
            'versionId': version_id,
            'cycleId': cycle_id,
            'projectId': project_id,
            'status': exec_status,
            'comment': exec_log[:700] if exec_log else ''
        }

        url = _Zephyr.baseURL + '/rest/zapi/latest/execution'
        headers = _headers()
        request = Request(url, data=dumps(json_data), headers=headers)
        js_res = urlopen(request)
        resp_json = load(js_res)

        for k, v in resp_json.iteritems():
            logger.debug('Test execution added. ID is: %s', k)
            execution_id = k

        if not execution_id:
            logger.error('Test execution adding failed: %s', resp_json)
            return
    elif int(cur_exec_status) == exec_status:
        # To be able to update execution time, we need first change status.
        # url = _Zephyr.baseURL + '/rest/zapi/latest/execution/%s/quickExecute' % execution_id  # does not work anymore?
        url = _Zephyr.baseURL + '/rest/zapi/latest/execution/%s/execute' % execution_id
        json_data = {
            'status': 3  # WIP -- work in progress
        }
        request = Request(url, data=dumps(json_data), headers=headers)
        request.get_method = lambda: 'PUT'
        urlopen(request)
        logger.info('Test execution status set to WIP. ID: %s', execution_id)

    json_data = {
        'status': exec_status,
        'comment': exec_log[:700] if exec_log else ''
    }

    url = _Zephyr.baseURL + '/rest/zapi/latest/execution/%s/execute' % execution_id
    request = Request(url, data=dumps(json_data), headers=headers)
    request.get_method = lambda: 'PUT'
    js_res = urlopen(request)
    resp_json = load(js_res)
    logger.info('Test execution updated. ID: %s', resp_json['id'])
    return execution_id


def _zephyr_find_test_step(issue_id, step):
    """
    Retrieve Zephyr test step id by 'issueId` and `step`
    """
    url = _Zephyr.baseURL + '/rest/zapi/latest/teststep/' + issue_id
    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)
    for item in resp_json:
        if 'step' in item and item['step'] == step:
            logger.debug('Test step found. ID is: %s', item['id'])
            return str(item['id'])

    logger.info('Test step "%s" not found.', step)
    return None


def _zephyr_add_test_step(issue_id, step, data, result):
    """
    Add test step for issue with id `issueId` using provided `step`, `data` and `result`
    """
    step_id = _zephyr_find_test_step(issue_id, step)

    json_data = {
        'step': step,
        'data': data,
        'result': result
    }

    headers = _headers()
    url = _Zephyr.baseURL + '/rest/zapi/latest/teststep/' + issue_id

    if step_id:
        url += '/' + step_id

    request = Request(url, data=dumps(json_data), headers=headers)

    if step_id:
        request.get_method = lambda: 'PUT'

    js_res = urlopen(request)
    resp_json = load(js_res)
    logger.debug('Test step created ID: %s', resp_json['id'])
    return str(resp_json['id'])


def _zephyr_find_step_result_id(step_id, execution_id):
    """
    Retrieve Zephyr test step execution by 'stepId` and `executionId`
    """
    url = _Zephyr.baseURL + '/rest/zapi/latest/stepResult/?executionId=' + execution_id
    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)
    for item in resp_json:
        if str(item['stepId']) == step_id:
            logger.debug('Test step result found. ID is: %s', item['id'])
            return str(item['id'])


def _zephyr_execute_test_step(step_id, execution_id, status, comment):
    """
    Create Zephyr test step with id `stepId` execution using provided `status`, `comment` and `executionId`
        |
    """
    step_result_id = _zephyr_find_step_result_id(step_id, execution_id)
    if not step_result_id:
        return

    url = _Zephyr.baseURL + '/rest/zapi/latest/stepResult/' + step_result_id
    logger.debug('Updating step result: %s', url)

    if isinstance(status, basestring):  # pass numeric status as is
        if status == 'PASS':
            status = 1
        elif status == 'FAIL':
            status = 2
        else:
            status = -1

    json_data = {
        'status': status,
        'comment': comment[:700] if comment else ''
    }
    headers = _headers()
    request = Request(url, data=dumps(json_data), headers=headers)
    request.get_method = lambda: 'PUT'
    js_res = urlopen(request)
    resp_json = load(js_res)
    logger.debug('Test step %s executed.', step_id)
    return str(step_result_id)


def _zephyr_get_version_id(project_key, version):
    """
    Return Jira project version id for project with key `projectKey` and version name `version`
    """
    url = _Zephyr.baseURL + '/rest/api/2/project/' + project_key + '/versions'

    logger.debug('Looking for versions: %s', url)

    headers = _headers()
    request = Request(url, headers=headers)
    js_res = urlopen(request)
    resp_json = load(js_res)

    for v in resp_json:
        if v['name'] == version:
            return v['id']

    return None


def _zephyr_attach_log(z, entity_id, entity_type, log_path):
    """
    Attach file `logPath` to Zephyr test execution step with id `stepResultId`
    """
    log_file = str(os.path.basename(log_path))

    url = z['baseURL'] + '/rest/zapi/latest/attachment?entityId=' + entity_id + '&entityType=' + entity_type
    headers = {'X-Atlassian-Token': 'nocheck', 'Accept': 'application/json'}

    with open(log_path, 'rb') as f:
        files = {'file': (log_file, f, 'multipart/form-data')}
        post(url, files=files, headers=headers, auth=HTTPBasicAuth(z['_username'], z['_password']))


def _zephyr_attach_test_step_log(z, step_result_id, log_path):
    '''
    Attaches log to test execution step result.

    :param step_result_id:
    :param log_path:
    :return:
    '''
    _zephyr_attach_log(z, step_result_id, 'TESTSTEPRESULT', log_path)


def _zephyr_attach_test_execution_log(z, execution_id, log_path):
    '''
    Attaches log to test execution.

    :param execution_id:
    :param log_path:
    :return:
    '''
    _zephyr_attach_log(z, execution_id, 'EXECUTION', log_path)


def _headers():
    '''
    Creates dict containing authorization and content type headers.

    :return: dict
    '''
    headers = {'Authorization': ' Basic ' + b64encode(_Zephyr._username + ':' + _Zephyr._password),
               'Content-Type': 'application/json'}
    return headers


def gen_report(z, path, test):
    if 'stepResultId' in test:
        gen_test_step_report(z, path, test)
    elif 'executionId' in test:
        gen_test_case_report(z, path, test)


def gen_test_step_report(z, path, test):
    """
    Generate test report for `test` and store it to file `${stepResultId}.html` in directory `path`
    """
    step_result_id = str(test['stepResultId'])
    log_path = str(os.path.dirname(path) + '/' + step_result_id + '.html')
    try:
        rebot_cli(['--test', str(test['longname']), '--report', 'NONE', '--log', log_path, str(path)])
    except SystemExit:
        pass
    except:
        logger.error('Unexpected error: %s', sys.exc_info()[0])

    _zephyr_attach_test_step_log(z, step_result_id, log_path)
    os.remove(log_path)


def gen_test_case_report(z, path, test):
    """
    Generate test report for `test` and store it to file `${stepResultId}.html` in directory `path`
    """
    execution_id = str(test['executionId'])
    log_path = str(os.path.dirname(path) + '/' + execution_id + '.html')
    try:
        rebot_cli(['--test', str(test['longname']), '--report', 'NONE', '--log', log_path, str(path)])
    except SystemExit:
        pass
    except:
        logger.error('Unexpected error: %s', sys.exc_info()[0])

    _zephyr_attach_test_execution_log(z, execution_id, log_path)
    os.remove(log_path)


def split_metadata_value(value):
    """
    Split and strip metadata string
    """
    if not value:
        return []

    value = value.strip()

    res = re.split(r'[,|]\s*', value)

    res = map(lambda v: v.strip().strip('|').strip(','), res)

    return res
