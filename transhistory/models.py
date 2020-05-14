# -*- coding: utf-8 -*-
'''
Created on Mar 22, 2011

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
from django.db import models
from django.db.models.base import ModelBase
from django.contrib.auth.models import User
from django.db.models import Q, Model

from .managers import RevisionManager
from transhistory import history_db

__all__ = ['Revision', 'TransHistoryMixin']

class Revision(models.Model):
    '''
    A Revision identifies database state at a point in time.
    '''
    objects = RevisionManager()
    '''
    transaction id is internal postgresql id for currently running transaction.
    They are unique within postgres installation, but if database is dumped and restored
    on another postgres instance, then the transaction ids may overlap.

    In case of database dump&restore: if the transaction IDs in the new database instance
    are smaller than those used in the backup, then it is necessary to reset all pg_transaction_id's to 0.
    '''
    pg_transaction_id = models.BigIntegerField(db_index=True)
    '''

    '''
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    '''
    TODO: time of last change in this revision
    '''
    committed_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Optionally it is possible to store the username of the user who changed the data.
    # Note that because Revisions may outlive Users, we can not use a real foreign key here.
    # If your application is not using django.contrib.auth.User to identify users,
    # you can store the relevant id in this field.

    committer = models.IntegerField(null=True, blank=True, db_index=True)
    # TODO: do we need a place for auxiliary data in each Revision?
    # admin_note = models.CharField(max_length=200)

    @staticmethod
    def set_committer(self, committer_id):
        '''
        Set the committer for the current transaction.
        '''

    def get_changed_objects(self, cls):
        pass

    def view(self, queryset):
        '''
        Provide a view to the database at this revision.
        Given a queryset of <Name>History objects, return another queryset which contains only those
        <Name>History objects that were in existence at this revision.
        conditions:
        - deleted_at_rev > self.id or deleted_at_rev is None
        - created_at_rev >= self.id
        - obsoleted_at_rev > self.id or obsoleted_at_rev is None

        If the queryset contains multiple objects with the same identity_id,
        the result will only contain at most one object for that identity_id.
        Remove objects that were created in the future.
        '''
        return Revision.view_at_revision(self.id, queryset)

    def get_object_version(self, object_or_class, object_pk=None):
        return Revision.get_object_at_revision(self.pk, object_or_class, object_pk)

    @staticmethod
    def get_object_at_revision(revision, object_or_class, object_pk=None):
        '''
        If object_pk is specified, then object_or_class parameter must be model class.
        If object_pk is not specified, then object_or_class parameter must be model instance.

        revision can be either a Revision instance or a revision id.
        Return an instance of the *History model.
        e.g. Revision.get_object_at_revision(some_rev_id, models.Cheese, my_object_id)
        If object is not found, then return None

        NOTE: if revision_id refers to a revision that was created in a transaction that was committed,
        and all earlier revisions have also been committed, then the result is cacheable, unless
        schema changes. Caching is currently not implemented.
        '''
        if object_pk is None:
            if not isinstance(object_or_class, Model):
                raise Exception('get_object_at_revision: instance of a django.db.Model expected: %s, got a: %s' % (object_or_class, type(object_or_class)))
            object_or_class, object_pk = type(object_or_class), object_or_class.pk
        hist_model = history_db.get_history_model(object_or_class)
        qs = hist_model.objects.filter(identity_id=object_pk).order_by() # order_by() to avoid extra join, if default ordering is specified
        rev_qs = Revision.view_at_revision(revision, qs)
        if rev_qs:
            if len(rev_qs) != 1:
                raise Exception('get_object_at_revision: too many objects (internal error, please report bug): %s' % qs)
            return rev_qs[0]
        return None


    @staticmethod
    def view_at_revision(revision, queryset):
        # provides the same functionality as "view"
        # revision can be either Revision object or revision id

        # isnull comparison results in extra join:
        # https://code.djangoproject.com/ticket/10790

        #ret = queryset.filter()
        # remove objects that were already deleted at this Revision
        # qs = qs.filter(Q(deleted_at_rev__isnull=True) or Q(deleted_at_rev__id__gt=self.pk))
        # now the list may still contain multiple versions of the same object.

        #ret = queryset.filter(created_at_rev__id__lte=revision_id)
        # node no longer exists at obsoleted_at_rev

        # isnull=True comparison results in extra join, must use negated query to avoid it
        # https://code.djangoproject.com/ticket/10790
        if isinstance(revision, Revision):
            revision = revision.pk
        ret = queryset.filter(~Q(obsoleted_at_rev__isnull=False) | Q(obsoleted_at_rev__id__gt=revision), created_at_rev__id__lte=revision)
        # ret = ret.filter(Q(obsoleted_at_rev__isnull=True) or Q(obsoleted_at_rev__id__gt=revision_id))
        #ret = ret.select_related('created_at_rev') # may speed up access to timestamps etc?
        # DEBUG ONLY
        #if NODECACHE_DEBUG:
        #    # util.debug_queryset(queryset, 'to_rev output')
        #    iids = []
        #    for sn in ret:
        #        ident = sn.get_ident()
        #        iids.append(ident.id)
        #        util.validate(ident.deleted_at_rev_id == None or ident.deleted_at_rev_id > target_rev_id,
        #                      'ERROR 6903234: deleted idents in retval - inconsistent database %s', ident,
        #                      exc_type=dwsexception.DwsInternalError)
        #
        #    util.validate_equals(len(iids), len(Set(iids)),
        #                         'ERROR 73242342: duplicate idents in: %s', iids,
        #                         exc_type=dwsexception.DwsInternalError)
        return ret



    def __unicode__(self):
        return 'Revision %s (tx%s) at %s by %s' % (self.id, self.pg_transaction_id, self.created_at, self.committer or 'unknown')

# TODO: base class
# NOTE: can not define base class straightforwardly!
#       the related_name of FK field gets duplicated because all *History models refer to Revision
#
#class TransHistoryModel(models.Model):
#    '''
#    This model represents the m2m intermediary table.
#    Subclass naming convention follows convention modelname+fieldname+'History', in CamelCase.
#    '''
#    vid = models.AutoField(primary_key=True)
#
#
#    '''
#    id of the object in main (non-history)table
#    Django m2m tables do have a unique primary key, although it is not normally visible through Django ORM.
#    NOTE: if using non-integer primary key, must not inherit from TransHistoryModel, must define history fields manually instead.
#    '''
#    identity_id = models.IntegerField(db_index=True)
#    created_at_rev = models.ForeignKey(Revision, related_name='created_employees_set')
#    """
#    obsoleted_at_rev:
#    The version _no longer exists_ in obsoleted_at_revision.
#    If the current latest node is replaced by new latest node, then obsoleted_at_rev == <nextnode>.created_at_rev
#    if the row is deleted from the main (Employee) table, obsoleted_at_rev is set and no new row is created in history table.
#
#    TODO: is it possible to maintain constraint created_at_rev < obsoleted_at_rev always???
#
#    Constraint: if obsoleted_at_rev is set to X, then one of the following must be true:
#    A. there exists one another ***History object with same identity_id and created_at_rev set to X.
#    B. deleted_at_rev field is also set to X.
#
#    Constraint: for each identity_id, at most one row may have obsoleted_at_rev set to NULL.
#
#    Constraint: (identity_id, created_at_rev) is unique together
#    Constraint: (identity_id, obsoleted_at_rev) is unique together
#
#    """
#    obsoleted_at_rev = models.ForeignKey(Revision,
#            related_name='obsoleted_employees_set', null=True, blank=True)
#
#    '''
#    deleted_at_rev is NULL except after row is removed from the main table.
#    to make queries easier, deleted_at_rev is set in all versions, not just the most recent one.
#    '''
#    deleted_at_rev = models.ForeignKey(Revision,
#            related_name='deleted_employees_set', null=True, blank=True)
#    class Meta:
#        abstract = True
#


# Maybe we someday find a need for subclassing ModelBase?
#class HistoryModelBase(ModelBase):
#    '''

    #objects = HistoryManager()
    #all_objects = models.Manager()
#    pass

#class ManyToManyHistoryModelBase(HistoryModelBase):
#    pass


class TransHistoryMixin(object):
    '''
    Mixin class that is intended to be applied to Django models.
    Only apply to models that have a corresponding <modelname>History model.

    This class provides convenience methods for accessing
    the history database. It is not necessary to use this mixin.
    If you can not or don't want to change the code of your models,
    you can access the history models directly or use the API
    in transhistory.models.Revision.
    '''
    def get_old_version(self, revision):
        '''
        Return most recent entry from the *History table that
        was created at or after revision.
        The revision parameter can be either numeric revision id
        or a transhistory.models.Revision object.
        '''
        return Revision.get_object_at_revision(revision, self)

