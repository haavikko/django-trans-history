# -*- coding: utf-8 -*-
'''
Created on May 22, 2011

@author: mhaa
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
from builtins import object
import logging

class PostgresLogStream(object):
    '''
    Utility for writing debug messages to postgresql server log.
    Used for django-trans-history development.
    '''
    def write(self, msg):
        # import here to avoid circular import - this is debug only so performance
        # does not matter, and import is cached anyway.
        from transhistory import backend
        backend.get_history_backend().write_to_db_log(msg)
    
    def flush(self):
        '''
        not needed
        '''
        pass

class PostgresLogHandler(logging.StreamHandler):
    '''
    Handler for logging into postgresql server log.
    '''
    def __init__(self, *args, **kwargs):
        #super(PostgresLogHandler, self).__init__(PostgresLogStream())
        #kwargs['stream'] = PostgresLogStream()
        logging.StreamHandler.__init__(self, PostgresLogStream())
