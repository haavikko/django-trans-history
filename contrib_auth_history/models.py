# -*- coding: utf-8 -*-
'''
Created on Jun 23, 2011

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

from transhistory.models import Revision

class UserHistory(models.Model):
    '''
    Track changes to contrib.auth.models.User model
    '''
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True) # id of the object in Organization table
    created_at_rev = models.ForeignKey(Revision, related_name='created_auth_user_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_auth_user_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_auth_user_set', null=True, blank=True)

    username = models.CharField(max_length=100, db_index=True) # field length can be larger than in actual table
    first_name = models.CharField(max_length=50, db_index=True)
    last_name = models.CharField(max_length=50, db_index=True)
    email = models.CharField(max_length=75, db_index=True)
    password = models.CharField(max_length=128)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    is_superuser = models.BooleanField()
    last_login = models.DateTimeField(null=True, blank=True) # don't need to specify default
    date_joined = models.DateTimeField(null=True, blank=True) # don't need to specify default

    def __unicode__(self):
        return '%s' % self.__dict__

    class TransHistory(object):
        target_app_label = 'auth'
        m2m_fields = ['groups', 'user_permissions']

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

class UserGroupsHistory(models.Model):
    '''
    Maintain group change history of contrib.auth user.
    '''
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True)
    created_at_rev = models.ForeignKey(Revision, related_name='created_user_groups_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_user_groups_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_user_groups_set', null=True, blank=True)

    user_id = models.IntegerField(db_index=True)
    group_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return '%s' % self.__dict__

    class TransHistory(object):
        target_app_label = 'auth'
        m2m_fields = ['groups']

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

class UserUserPermissionsHistory(models.Model):
    '''
    Maintain user_permissions change history of contrib.auth user.
    '''
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True)
    created_at_rev = models.ForeignKey(Revision, related_name='created_user_user_permission_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_user_user_permission_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_user_user_permission_set', null=True, blank=True)

    user_id = models.IntegerField(db_index=True)
    permission_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return '%s' % self.__dict__

    class TransHistory(object):
        target_app_label = 'auth'

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

class PermissionHistory(models.Model):
    '''
    Maintain change history of contrib.auth permission.
    '''
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True) # id of the object in Organization table
    created_at_rev = models.ForeignKey(Revision, related_name='created_permission_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_permission_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_permission_set', null=True, blank=True)

    name = models.CharField(max_length=100, db_index=True) # field length can be larger than in actual table
    content_type_id = models.IntegerField(max_length=50, db_index=True)
    codename = models.CharField(max_length=100, db_index=True)

    def __unicode__(self):
        return '%s' % self.__dict__

    class TransHistory(object):
        target_app_label = 'auth'

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

class GroupHistory(models.Model):
    '''
    Maintain change history of contrib.auth group.
    '''
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True) # id of the object in Organization table
    created_at_rev = models.ForeignKey(Revision, related_name='created_group_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_group_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_group_set', null=True, blank=True)

    name = models.CharField(max_length=100, db_index=True) # field length can be larger than in actual table
    content_type_id = models.IntegerField(max_length=50, db_index=True)
    codename = models.CharField(max_length=100, db_index=True)

    def __unicode__(self):
        return '%s' % self.__dict__

    class TransHistory(object):
        target_app_label = 'auth'
        m2m_fields = ['permissions']

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

class GroupPermissionsHistory(models.Model):
    '''
    Maintain change history of contrib.auth group permissions.
    '''
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True)
    created_at_rev = models.ForeignKey(Revision, related_name='created_group_permission_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_group_permission_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_group_permission_set', null=True, blank=True)

    group_id = models.IntegerField(db_index=True)
    permission_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return '%s' % self.__dict__

    class TransHistory(object):
        target_app_label = 'auth'

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)
