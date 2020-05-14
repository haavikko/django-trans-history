# -*- coding: utf-8 -*-
'''
Created on Apr 26, 2011

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
__all__ = ['get_history_backend', 'HistoryBackend']

def get_history_backend():
    '''
    Return the currently active history backend.
    
    TODO: make configurable
    '''
    from transhistory import postgresql
    return postgresql.history_backend

class HistoryBackend(object):
    '''
    TODO: if/when additional backends are added, define common interface here.
    
    (such as: mysql/django signal-based)
    '''
    pass

