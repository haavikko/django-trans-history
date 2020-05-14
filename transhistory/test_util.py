# -*- coding: utf-8 -*-
'''
Created on Jun 22, 2011

@author: mhaa
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import *
import os
import functools
from django.db import connection

from django.db import transaction
from django.test import TransactionTestCase

import logging
logger = logging.getLogger(__name__)

def log_exceptions(func):
    """
    log exceptions, pass them on.
    Workaround for: http://code.djangoproject.com/ticket/6623
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            logger.error('uncaught exception in %s', func.__name__, exc_info=True)
            raise
    return wrapper

_tmpnam_counter = 0

class HistoryTransactionTestCase(TransactionTestCase):
    '''
    Base class for transactional tests.

    Changed logic to capture last executed SQL:
    * logging sql queries
    * settings.DEBUG=True (change from default so that SQL is logged, see http://code.djangoproject.com/ticket/8401)
    '''
    def __call__(self, result=None):
        logger.debug('running: %s', self._testMethodName)
        try:
            from django.conf import settings
            settings.DEBUG=True

            log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO'))
            logging.getLogger('dws').setLevel(log_level)

            django_level = getattr(logging, os.getenv('DJANGO_LOG_LEVEL', 'ERROR'))
            logging.getLogger('django').setLevel(django_level)
            logging.getLogger('request').setLevel(django_level)
            logging.getLogger('django.db.backends').setLevel(django_level)
            ret = super(TransactionTestCase, self).__call__(result)
            logger.debug('done: %s %s', self._testMethodName, ret)

            return ret
        except:
            logger.error('testcase fail: %s', self._testMethodName, exc_info=True)
            logger.error('last 5 sql queries: %s', connection.queries[-5:])
            raise

    def tmpnam(self, strval):
        '''
        used to generate unique test data in loops etc.
        '''
        global _tmpnam_counter
        _tmpnam_counter += 1
        ret = '%s_%s_%s' % (self._testMethodName, _tmpnam_counter, strval)
        logger.debug('tmpname %s', ret)
        return ret


def is_running_tests():
    import sys
    return 'manage.py' in sys.argv and 'test' in sys.argv

try:
    # if running in mod_wsgi do not invoke debugger as it just fails the request
    # http://modwsgi.readthedocs.io/en/develop/user-guides/assorted-tips-and-tricks.html
    from mod_wsgi import version
    set_trace = lambda: None
except:
    # get proper function for invoking debugger
    if is_running_tests():
        # need to disable stdout redirection
        # also, we do not want to introduce additional stack frame to make debugging easier
        import nose
        set_trace = nose.tools.set_trace
    else:
        import pdb
        set_trace = pdb.set_trace

