import ZephyrLibrary
from ZephyrLibrary import _Zephyr, ZephyrLibrary as ZL
from robot.libraries.BuiltIn import BuiltIn, EXECUTION_CONTEXTS
from robot.running.namespace import Namespace
from robot.running.model import TestSuite
from robot.variables.variables import Variables
from . import Dotable


class ZephyrMock(_Zephyr):

    expected = {}

    def _process_test_suite(self, project_key, suite_summary, suite_description, issue_custom_field,
                            issue_custom_field_val, execution_status, execution_log):
        print self._metadata, ZephyrMock.expected
        if self._metadata != ZephyrMock.expected:
            raise AssertionError('Expected metadata in not equals to actual.')


def _bootstrap_robot():
    BuiltIn()
    v = Variables()
    v['${zephyr}'] = Dotable.parse({'baseURL': 'qwe', 'user': 'qwe', 'passwd': 'qwe', 'project_key': 'TEST', 'custom_field_id': 'custom_field_id'})
    v['${/}'] = '/'
    EXECUTION_CONTEXTS.start_suite(Namespace(TestSuite(), v, None, [], []), 'qwe')


def test_paths():
    _bootstrap_robot()

    l = ZL()
    l._ZephyrLibrary__delegate = ZephyrMock()

    l.start_suite('test', {'source': '/home/asd', 'metadata': {'test': 'test'}})
    l.start_suite('test', {'source': '/home/asd/qwe.robot', 'metadata': {'test': 'test1'}})
    ZephyrMock.expected = {'test': 'test1'}
    l._ZephyrLibrary__delegate._empty_suite = False
    l.end_suite('test', {'longname': '', 'doc': '', 'status': '', 'statistics': '', 'source': '/home/asd/qwe.robot', 'metadata': {}})
    l.start_suite('test', {'source': '/home/asd/asd.robot', 'metadata': {}})
    ZephyrMock.expected = {'test': 'test'}
    l._ZephyrLibrary__delegate._empty_suite = False
    l.end_suite('test', {'longname': '', 'doc': '', 'status': '', 'statistics': '', 'source': '/home/asd/asd.robot', 'metadata': {}})
    l.end_suite('test', {'longname': '', 'doc': '', 'status': '', 'statistics': '', 'source': '/home/asd/asd', 'metadata': {}})


def test_windows_paths():
    _bootstrap_robot()

    ZephyrLibrary._IS_WINDOWS = True
    l = ZL()
    l._ZephyrLibrary__delegate = ZephyrMock()

    l.start_suite('test', {'source': 'C:\\Program Files\\Asd', 'metadata': {'test': 'test'}})
    l.start_suite('test', {'source': 'C:\\Program Files\\Asd\\qwe.robot', 'metadata': {'test': 'test1'}})
    ZephyrMock.expected = {'test': 'test1'}
    l._ZephyrLibrary__delegate._empty_suite = False
    l.end_suite('test', {'longname': '', 'doc': '', 'status': '', 'statistics': '', 'source': 'C:\\Program Files\\Asd\\qwe.robot', 'metadata': {}})
    l.start_suite('test', {'source': 'C:\\Program Files\\Asd\\asd.robot', 'metadata': {}})
    ZephyrMock.expected = {'test': 'test'}
    l._ZephyrLibrary__delegate._empty_suite = False
    l.end_suite('test', {'longname': '', 'doc': '', 'status': '', 'statistics': '', 'source': 'C:\\Program Files\\Asd\\asd.robot', 'metadata': {}})
    l.end_suite('test', {'longname': '', 'doc': '', 'status': '', 'statistics': '', 'source': 'C:\\Program Files\\Asd', 'metadata': {}})


if __name__ == '__main__':

    #print l.__default_zephyr._zephyr_find_test( "http://0.0.0.0.0:48080", 'divya', "automation", "10100", "zephyr\zephyrTest.robot", "TP")
    #print l.__default_zephyr._zephyr_create_or_update("http://0.0.0.0.0:48080", 'divya', "automation", "zephyrTest", "Suite description", "10100", "zephyr\zephyrTest.robot", "TP")
    #print l.__default_zephyr._get_project_id("http://0.0.0.0.0:48080", 'divya', "automation", "TP")
    #print l.__default_zephyr._zephyr_find_test_cycle("http://0.0.0.0.0:48080", 'divya', "automation", "ZZZ", "TP", "10000")
    #print l.__default_zephyr._zephyr_create_test_cycle("http://0.0.0.0.0:48080", 'divya', "automation", "SSS", "TP", "10000")
    #print l.__default_zephyr._zephyr_add_test_to_cycle("http://0.0.0.0.0:48080", 'divya', "automation", "7", "TP-11", "10000", "-1")
    # print l.__default_zephyr._zephyr_execute_test("http://0.0.0.0.0:48080", 'divya', "divya", "7", "TP-11", "10000", "-1", "PASSED", "Execution log")
    # print l.__default_zephyr._process_test_suite("http://0.0.0.0.0:48080", 'divya', "divya", "zephyrTest", "Suite description", "10100", "zephyr\zephyrTest.robot", "TP", "-1", "PASSED", "My exec log")

    test_paths()
    test_windows_paths()
