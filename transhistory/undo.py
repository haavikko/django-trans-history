# -*- coding: utf-8 -*-
'''
Created on Apr 26, 2011

@author: mhaa

Common internal utilities

'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
import itertools
import datetime
import string
import logging

from transhistory import history_db, Revision

from django.db.transaction import atomic
from django.contrib.contenttypes.fields import GenericRelation
import collections

logger = logging.getLogger(__name__)

'''
Undoing changes:
* Undo delete: Restore object that was deleted
* Undo modify: Restore object to the previous state
* Undo create: Delete an object that was created

How to avoid foreign key conflicts:
* Suppose A has foreign key to B.
** Need to restore B first so that we can set the FK value in A.
** In Postgres

TODO need to think about undo api!
'''

def undo_delete(model_class, primary_key):
    pass

def undo_changes(obj, restore_to_revision):
    pass

def undo_create(obj):
    pass


def restore_to_revision(obj, rev):
    '''
    Load old version of object from history and save it as a new object.
    '''
