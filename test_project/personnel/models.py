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

from transhistory.models import Revision, TransHistoryMixin
from transhistory.managers import HistoryManager
#, HistoryManager, HistoryModel, ManyToManyHistoryModel

__all__ = ['Employee', 'Organization', 'EmployeeHistory', 'OrganizationHistory', 'EmployeeOrganizationsHistory', 'UserHistory']

class Employee(models.Model, TransHistoryMixin):
    '''
    Test data for django-trans-history.

    test replacing objects with history-aware manager
    '''
    #objects = transhistory.HistoryManager()

    first_name = models.CharField(max_length=50, db_index=True)
    last_name = models.CharField(max_length=50, db_index=True)

    '''
    test history of m2m fields
    '''
    organizations = models.ManyToManyField('Organization', related_name='employee_set')

    '''
    test multiple foreign keys to same model
    '''
    primary_organization = models.ForeignKey('Organization', null=True, blank=True, related_name='primary_employee_set')
    cost_center = models.ForeignKey('Organization', related_name='cost_center_employee_set')

    def __unicode__(self):
        return '%s' % self.__dict__


#EmployeeHistory = transhistory.history_class(Employee)

class Organization(models.Model):
    # NOTE: note using TransHistoryMixin. The system must be able to operate without it.
    name = models.CharField(max_length=50, db_index=True)

    '''
    Test data for django-trans-history.

    test foreign key to same model
    '''
    parent_organization = models.ForeignKey('Organization', null=True, blank=True)

    def __unicode__(self):
        return '%s' % self.__dict__


class EmployeeHistory(models.Model):
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True) # id of the object in Employee table
    created_at_rev = models.ForeignKey(Revision, related_name='created_employees_set')
    """
    obsoleted_at_rev:
    The version _no longer exists_ in obsoleted_at_revision.
    If the current latest node is replaced by new latest node, then obsoleted_at_rev == <nextnode>.created_at_rev
    if the row is deleted from the main (Employee) table, obsoleted_at_rev is set and no new row is created in history table.

    TODO: is it possible to maintain constraint created_at_rev < obsoleted_at_rev always???

    Constraint: if obsoleted_at_rev is set to X, then one of the following must be true:
    A. there exists one another ***History object with same identity_id and created_at_rev set to X.
    B. deleted_at_rev field is also set to X.

    Constraint: for each identity_id, at most one row may have obsoleted_at_rev set to NULL.

    Constraint: (identity_id, created_at_rev) is unique together
    Constraint: (identity_id, obsoleted_at_rev) is unique together

    """
    obsoleted_at_rev = models.ForeignKey(Revision,
            related_name='obsoleted_employees_set', null=True, blank=True)

    '''
    deleted_at_rev is NULL except after row is removed from the main table.
    to make queries easier, deleted_at_rev is set in all versions, not just the most recent one.
    '''
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_employees_set', null=True, blank=True)

    # field names must correspond to field names in Employee
    first_name = models.CharField(max_length=50, db_index=True)
    last_name = models.CharField(max_length=50, db_index=True)

    # not storing the operation code (create/update/delete). Operation type can be determined:
    # - when row is created in the main table, first row is added to EmployeeHistory
    #   the first row in history table is result of create operation.
    # - when row is modified in the main table, new rows are added for each modification.
    #   the new row in history table will have NULL obsoleted_at_rev, indicating that the row still exists in the main table.
    #   TODO: if row is modified multiple times,
    # - when row is deleted from the main table, last row is added to EmployeeHistory.
    #
    '''
    test history of m2m fields
    '''
    # NOTE: m2m fields in separate model

    '''
    test multiple foreign keys to same model
    '''
    primary_organization_id = models.IntegerField(null=True, blank=True, db_index=True)
    cost_center_id = models.IntegerField(null=True, blank=True, db_index=True) # TODO: although cost_center is not NULLable, should we make it NULLable here in case the column is ever removed?

    def __unicode__(self):
        return '%s' % self.__dict__

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

    class TransHistory(object):
        '''
        test field exclusion
        '''
        fields = ['first_name', 'organizations', 'primary_organization', 'cost_center']

        #    # NOTE: Employee.organizations.field.m2m_db_table() returns the database table name
        #    m2m_relation = Employee.organizations

        '''
        test custom timestamp columns
        '''
        last_modified_field = 'custom_last_modified' # defaults to 'last_modified'
        last_modified_by_field = 'changed_by' # defaults to 'last_modified_by'

        #'''
        #trans-history needs a way to uniquely identify every object in the database.
        #Usually, primary key is not sufficient since another row in another table might have the same primary key.
        #Here, we are telling the system that the primary key is known to be unique across all tables.
        #(e.g. you are using UUIDs as the primary key)
        #'''
        #globally_unique_primary_key = True


class OrganizationHistory(models.Model):
    # TODO: create a subclass of IntegerField that provides a nicer display in admin
    # TODO: make all history entries non-editable in admin
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True) # id of the object in Organization table
    # TODO: For convenience, we may define a ForeignKey back to the organization main table.
    # The drawback is that once the row is removed from the main table, the foreign key constraint
    # no longer applies.
    # Must always remember to specify on_delete behavior as SET_NULL, or the object is cleared from history table too.
    # TODO: do we require "on delete set null" in the database also?
    # organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL)
    created_at_rev = models.ForeignKey(Revision, related_name='created_organizations_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_organizations_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_organizations_set', null=True, blank=True)

    name = models.CharField(max_length=50, db_index=True)
    parent_organization_id = models.IntegerField(null=True, db_index=True)

    # TODO: It is possible to define additional fields in the history table.
    # These are not used by the history mechanism, so they should have reasonable default values.
    # my_extra_data = models.CharField(max_length=200)

    # easy access to reverse end of m2m data
    # employees = transhistory.ManyToManyHistory() # must have same name as field in Employee

    class TransHistory(object):
        '''
        test custom tablespace
        '''
        tablespace = 'my_table_space'

    def __unicode__(self):
        return '%s' % self.__dict__

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)


class EmployeeOrganizationsHistory(models.Model):
    '''
    This model represents the m2m intermediary table.
    Model name follows convention modelname+fieldname+'History', in CamelCase.
    '''
    vid = models.AutoField(primary_key=True)

    '''
    Django m2m tables do have a unique primary key, although it is not normally visible through Django ORM.
    '''
    identity_id = models.IntegerField(db_index=True)
    created_at_rev = models.ForeignKey(Revision, related_name='created_employee_organizations_set')
    obsoleted_at_rev = models.ForeignKey(Revision,
            related_name='obsoleted_employee_organizations_set', null=True, blank=True)

    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_employee_organizations_set', null=True, blank=True)

    employee_id = models.IntegerField(db_index=True) # id of the object in Employee table (also identity_id in EmployeeHistory table).
                                        # Can not use foreign key because:
                                        # 1. history must be maintained even if the original row from Employee is deleted
                                        # 2. identity_id in EmployeeHistory is not unique (NOTE: MySQL InnoDB allows
                                        #    foreign key to refer to non-unique column, but we are not using that feature)
    organization_id = models.IntegerField(db_index=True)

    def __unicode__(self):
        return '%s' % self.__dict__

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

class UserHistory(models.Model):
    # for testing django auth.user history - history is tracked in different app.
    vid = models.AutoField(primary_key=True)
    identity_id = models.IntegerField(db_index=True) # id of the object in Organization table
    created_at_rev = models.ForeignKey(Revision, related_name='created_user_set')
    obsoleted_at_rev = models.ForeignKey(Revision, related_name='obsoleted_users_set', null=True, blank=True)
    deleted_at_rev = models.ForeignKey(Revision,
            related_name='deleted_users_set', null=True, blank=True)

    username = models.CharField(max_length=50, db_index=True) # field length can be larger than in actual table
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
        m2m_fields = ['groups']

    class Meta(object):
        unique_together = (("created_at_rev", "identity_id"), ("obsoleted_at_rev", "identity_id"),)
        ordering = ("created_at_rev",)

class UserGroupsHistory(models.Model):
    # for testing django auth.user history
    # also test, that it is not required to track the reverse end of a m2m relation.
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


#class Vanilla(models.Model):
#    '''
#    test 'drop-in' history management: model is vanilla Django model without any code changes
#    '''
#    foo_field = models.CharField(max_length=20)
#
#
#class VanillaHistory(transhistory.HistoryModel):
#    pass


