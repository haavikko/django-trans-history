# -*- coding: utf-8 -*-
'''
Created on Apr 25, 2011

@author: mhaa
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
import datetime
import logging

from django.contrib.auth.models import User
from django.db import models
from django.db import connection

__all__ = ['HistoryManager', 'RevisionManager']

logger = logging.getLogger(__name__)

class RevisionManager(models.Manager):
    '''
    manager for Revision class, with extra history-related operations.
    '''
    @property
    def head(self):
        '''
        Return the current latest Revision.
        This is usually _not_ the Revision of the ongoing transaction, use "my" instead.
        '''
        return self.model.objects.order_by('-pk')[0]

    @property
    def my(self):
        '''
        Return the Revision for the current transaction.
        If one does not exist yet, it is created.

        NOTE: Most of the time, the ***History tables are updated at the _end_ of the transaction,
        meaning that this property does not allow querying for modifications done within this transaction.
        '''

        rev, created = self.th_update_or_create(pg_transaction_id=self._pg_txid_current(),
                              defaults={'committed_at': datetime.datetime.now()})
        #if created:
        #    logger.debug('RevisionManager created revision %s', rev.pk)
        return rev

    @property
    def current_revision(self):
        # If revision object for current transaction does not exist, return None
        # If revision has been created, return the revision object.
        return self.filter(pg_transaction_id=self._pg_txid_current()).first()

    def create_first(self):
        '''
        Ensure that the initial revision exists in the database
        (it is not strictly necessary but is useful, as the Revision.objects.head points to something always).
        '''
        if self.count() == 0:
            # transaction id 0 should not conflict?
            return self.create(pg_transaction_id=0, committed_at=datetime.datetime.now())
        return self.order_by('-pk')[0]

    def set_current_committer(self, user_id):
        '''
        Set the committer of the current transaction.
        An IntegerField is used to save the committer id. ForeignKey is not used because we want to retain
        the user id even if the actual user is deleted from the database.
        The id is not required to be the id of django.contrib.auth.User - if you have implemented your
        own user management, any id will do.

        It is possible to begin the transaction without knowing the actual user performing the operation,
        and specify the committer when user is known. That way, all database operations are attributed
        to the correct actor.

        The data model does not allow multiple committers per Revision. A new Revision (and new transaction)
        is needed in these cases.

        If a Revision does not yet exist at the time of calling this function, then one is created.
        committed_at timestamp is set to the current time, although that may change later if/when
        versioned objects are modified in the database.
        '''
        if isinstance(user_id, User):
            user_id = user_id.id
        self.th_update_or_create(pg_transaction_id=self._pg_txid_current(),
                              defaults={'committed_at': datetime.datetime.now(), 'committer':user_id})

    def th_update_or_create(self, **kwargs):
        """ based on: http://code.djangoproject.com/attachment/ticket/3182/update_or_create.diff

                     Looks up an object with the given kwargs, creating one if necessary.
                     If the object already exists, then its fields are updated with the
                     values passed in the defaults dictionary.
                     Returns a tuple of (object, created), where created is a boolean
                     specifying whether an object was created.

        obj, created = Person.objects.update_or_create(first_name='John', last_name='Lennon',
                                    defaults={'birthday': date(1940, 10, 9)})

        The non-atomicity described in the ticket does not concern us with Revisions, because
        we are using txid_current(), which is unique to the ongoing transaction.
        """
        obj, created = self.get_or_create(**kwargs)
        if not created:
            defaults = kwargs.pop('defaults', {})
            for k, v in defaults.items():
                setattr(obj, k, v)
            obj.save()
        return obj, created

    def _pg_txid_current(self):
        c = connection.cursor()
        c.execute('SELECT txid_current()')
        return c.fetchone()[0]

class HistoryManager(models.Manager):
    '''
    (TBD) Manager that presents a view of the database as it was at a certain Revision.
    By default, show the latest version of all objects (hiding deleted objects).
    '''

    def get_all_versions(self, obj):
        '''
        regardless of the currently selected Revision, return all versions of the supplied object.
        '''
        return []

