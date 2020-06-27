# !/usr/bin/env python2.7
# -*- coding: utf-8 -*-
from string import *
from robot.libraries.BuiltIn import BuiltIn
import re
import os.path

_D=_DESCRIPTION='descr'
_E=_EXAMPLE='example'
_A=_ARGUMENTS='args'
_X=_XPATH='xpath'
_C=_CSS='css'

_GET_LOCATOR='Get Locator'
_ELEMENT='Element'

_STRATEGY_RE=re.compile(r'^(' + _XPATH + '|' + _CSS + ')=(.*)')

class ElementLocatorsLibrary():
    """DOM elements locators library
    """
    def __init__(self, *locators_modules):

        self._builtIn = BuiltIn()

        self._locators = {}
        self._locators_module_names = {}

        for module in locators_modules:
            _locators_module = __import__(module, fromlist=['LOCATORS'])
            self._locators.update(_locators_module.LOCATORS)
            self._locators_module_names.update((k, module) for k in _locators_module.LOCATORS.keys())

        self._supported_strategies = [_XPATH, _CSS]
        self._parent_arg_name = 'parent'
        self._parent_arg_default_value = '${PARENT_ELEMENT}'
        self._axis_arg_name = 'axis'
        self._axis_arg_xpath_default_value = '//'

        for locator in self._locators.values():
            args = locator['args']
            if not any(arg.startswith(self._parent_arg_name + '=') for arg in args):
                args.append(self._parent_arg_name + '=' + self._parent_arg_default_value)
            if not any(arg.startswith(self._axis_arg_name + '=') for arg in args):
                args.append(self._axis_arg_name + '=' + (self._axis_arg_xpath_default_value if 'xpath' in locator else ' '))

    # Keyword methods
    def get_keyword_names(self):
        '''
        Returns all locator names
        '''
        return self._locators.keys() + [_GET_LOCATOR, _ELEMENT]

    def get_keyword_arguments(self, name):
        '''
        Returns arguments list of keyword with specified `name`
        '''
        if name == _GET_LOCATOR:
            return ['name', '*args']
        if name == _ELEMENT:
            return ['tag=', 'parent=${PARENT_ELEMENT}', 'axis= ', '*args']
        return self._locators.get(name)[_ARGUMENTS]

    def run_keyword(self, name, *args):
        '''
        Returns locator if `Get Locator` keyword is called or xpath if any Locator called directly.
        '''
        args = self.__normalize_args(*args)
        if name == _GET_LOCATOR:
            return self.__get_locator(*args)

        if name == _ELEMENT:
            return self.__get_element(*args)

        return self.__run_keyword(name, *args)

    def get_keyword_documentation(self, name):
        if name == "__intro__":
            return """
    This library is used to locate HTML elements on web pages.
    Each keyword included with this library returns a `locator` object that can subsequently be used for:
    - Define the [realtest.ui.selenium2.actions.robot.html|action] to be performed with the element;
    - Specify the `parent` element while creating locator for a child element.

    Please refer to the [realtest.ui.selenium2.actions.robot.html|UI Actions] documentation
    for possible actions that can be applied to the elements, as well as specific examples.

    Example usage:
    | ${b1}=      | Button | label=Save    |
    | ${b2}=      | Button | Save          |
    | ${parent}=  | Popup  | title=Confirm |
    | ${b3}=      | Button | label=Save    | parent=${parent} |

    == Narrowing locator scope using parent element  ==
    Each element keyword accepts the  `parent` parameter which can be set to a `locator` object of the parent
    element containing the actual element to be located.
    This can be used to narrow the search scope down to a specific container such as panel or popup
    and avoid picking up wrong elements.

    By default, the `parent` is set to the global value of ${PARENT_ELEMENT} variable which
    is being managed by the keywords `Add Context` and `Remove Context` defined
    at [realtest.ui.selenium2.actions.robot.html|actions library].
    """

        if name == "__init__":
            return "Python module with locators configuration, e.g. locators.py"
        if name == _GET_LOCATOR:
            return 'Returns the `locator` object using the keyword `element_keyword` with arguments `element_keyword_args`.' \
                   + '\nThis is utility keyword being used internally by most of the action keywords in this library.'
        if name == _ELEMENT:
            return 'Returns the `locator` for element with specified attributes.' \
                   + '\nThis is utility keyword being used internally by most of the action keywords in this library.'

        locator = self._locators.get(name)
        strategy = next(x for x in locator.keys() if x in self._supported_strategies)
        element_doc = locator[_DESCRIPTION] + "\n\n  Element xpath: `" + locator[strategy]
        try:
            element_example = locator[_EXAMPLE]
        except:
            return element_doc

        element_doc = element_doc + "\n\n For example: \n\n" + element_example

        path_to_png = self._locators_module_names.get(name).replace(".", "/").rpartition("/")[0] + \
                      "/doc/images/" + name + ".png"
        if os.path.isfile(path_to_png):
            element_doc = element_doc + "\n\n[../" + path_to_png + "|]"
        return element_doc

    # Private methods
    def __log(self, message, level='INFO', html=False, console=False, repr=False):
        '''
        BuiltIn.log wrapper.
        '''
        self._builtIn.log(message, level, html, console, repr)

    def __get_locator(self, *args):
        '''
        Returns locator of specified element. First argument is the name and other are arguments
        '''
        name = args[0]
        return self.run_keyword(name, *args[1:])

    def __get_element(self, *args):
        '''
        Gets element by any attribute. First item in args is tag name. Rest are key=value strings.
        :param args: tag name and attributes key/values
        :return: element locator
        '''
        template_string = self.__build_css_selector(*args)
        template = self.__template(template_string)
        return 'css=%s' % self.__transform(template, _ELEMENT, *args)

    def __build_css_selector(self, *args):
        template_string=args[0]
        for item in args[1:]:
            splitted = unicode(item).split('=', 1)
            if not splitted[0] in [self._axis_arg_name, self._parent_arg_name]:
                if splitted[0] == 'id':
                    template_string += '#' + splitted[1]
                elif splitted[0] == 'class':
                    template_string += '.' + splitted[1]
                elif not self.__islocator(item):
                    template_string += '[' + splitted[0] + '="' + splitted[1] + '"]'
        return template_string

    def __replace_vars(self, text):
        '''
        Replaces `text` containing reference to Test/Suite/Global variable with actual value.
        '''
        # Empty string?
        if not text:
            return text
        result = self._builtIn.replace_variables(text)
        # Empty string?
        if not result:
            return result
        return self.__strip_strategy(result)

    def __normalize_args(self, *args):
        '''
        Help method for normalizing keyword args in situations when we get tuple with arguments instead list
        '''
        # normalize args
        while isinstance(args, tuple) and len(args) == 1 and isinstance(args[0], tuple):
            args = args[0]
        return args

    def __islocator(self, obj):
        '''
        Checks if `obj` has locator format, i.e. starts with '/' or xpath= or css=
        '''
        if not isinstance(obj, basestring):
            return False
        return obj.startswith('/') or _STRATEGY_RE.match(obj)

    def __strip_strategy(self, locator):
        '''
        Get rid of prefix like xpath=/css= if present.
        '''
        matcher = _STRATEGY_RE.match(locator)
        if not matcher:
            return locator
        return matcher.group(2)

    def __run_keyword(self, name, *args):
        '''
        Returns locator by name specified.
        '''
        if self.__islocator(name):
            return name

        self.__log( 'Running keyword "%s" with arguments %s.' % (name, args) )
        locator = self._locators.get(name)

        if not locator:
            raise RuntimeError('Locator "%s" not found.' % name)

        # get the very first available strategy
        strategy = next(x for x in locator.keys() if x in self._supported_strategies)
        template_string = locator[strategy]
        template = self.__template(template_string)
        return '%s=%s' % (strategy, self.__transform(template, name, *args))

    def __transform(self, template, name, *args):
        d = dict()
        i = 0
        positional = True
        # fill dictionary d with default and positional arg values
        for item in self.get_keyword_arguments(name):
            self.__log( 'Template item is  "%s"' % (item,) )
            val = None
            splitted = item.split('=', 2)
            # print "Splitted item is  '%s'" % splitted
            if len(splitted) == 2:
                val = splitted[1]
            if positional and len(args) > i:
                # if this is locator, most likely this it's parent
                if count(unicode(args[i]), '=') > 0 and not self.__islocator(args[i]):
                    positional = False
                else:
                    val = unicode(args[i])
            if not val is None:
                d[splitted[0]] = self.__replace_vars(val)
            i += 1
        # fill dictionary d with named arg values
        for item in args:
            splitted = unicode(item).split('=', 1)
            if len(splitted) == 2:
                d[splitted[0] if not self.__islocator(item) else 'parent'] = self.__replace_vars(splitted[1])
        result = template.substitute(d).strip()
        self.__log( 'Result is  "%s"' % result )
        return result

    def __template(self, template_string):
        '''
        Generates Template from provided `template_string`. Will add ${self._parent_arg_name}${self._axis_arg_name} at
        the beginning of the template if `template_string` doesn't contain it.

        :param template_string:
        :return: template
        '''
        if '${' + self._axis_arg_name + '}' not in template_string:
            template_string = '${' + self._axis_arg_name + '}' + template_string
        if '${' + self._parent_arg_name + '}' not in template_string:
            template_string = '${' + self._parent_arg_name + '}' + template_string
        template = Template(template_string)
        return template
