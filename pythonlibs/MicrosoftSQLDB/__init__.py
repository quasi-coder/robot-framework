# !/usr/bin/env python2.7
# -*- coding: utf-8 -*-
import pymssql

__author__ = 'dwiveddi'
__version__ = '0.0.1'


def connect(database='', user='', password='', host='localhost', port=1433):
    '''
    Bridge between robot DatabaseLibrary and pymssql.

    :param database:
    :param user:
    :param password:
    :param host:
    :param port:
    :return: pymssql.Connection
    '''
    return pymssql.connect(database=database, server=host, port=port, user=user, password=password)