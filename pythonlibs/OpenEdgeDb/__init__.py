# !/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import pyodbc

__author__ = 'dwiveddi'
__version__ = '0.0.1'
__DEFAULT_DRIVER = '{OpenEdge Wire Protocol}'


def connect(database='', user='', password='', host='localhost', port=2055):
    '''
    Bridge between robot DatabaseLibrary and pyodbc.

    :param database:
    :param user:
    :param password:
    :param host:
    :param port:
    :return: pyodbc.Connection
    '''
    return pyodbc.connect(driver=__DEFAULT_DRIVER, database=database, hostname=host, port=port, uid=user,
                          password=password)