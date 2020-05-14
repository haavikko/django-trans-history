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
from django.db import transaction


from transhistory.models import Revision
from personnel.models import *
from transhistory.backend import get_history_backend
from django.core.management import call_command

import logging
logger = logging.getLogger(__name__)

from transhistory.test_util import HistoryTransactionTestCase, log_exceptions, set_trace

class A_InitHistoryTest(HistoryTransactionTestCase):
    '''
    Test creation of the history tables, database triggers and procedures.
    Needed by other tests.
    The tables are truncated by Django but the triggers remain installed.
    '''

    @transaction.atomic
    @log_exceptions
    def test_install(self):
        call_command('transhistory_syncdb', interactive=False)

        #self.init_plpgsql()
        #transhistory_install()
        get_history_backend().db_logging_enabled = True
        # EmployeeHistory.syncdb()

class PersonnelCrudTest(HistoryTransactionTestCase):
    '''
    Test that CRUD operations are recorded in the corresponding History table
    '''
    @log_exceptions
    def test_organization_crud(self):
        name1 = self.tmpnam('foo')

        with transaction.atomic():
            foo = Organization(name=name1)
            foo.save()
            revisions_count_0 = Revision.objects.count()
            # history must be created at transaction commit, not before
            self.assertEqual(0, OrganizationHistory.objects.filter(name=name1).count())
            self.assertEqual(0, Revision.objects.count() - revisions_count_0) # don't create Revision yet

        self.assertEqual(1, OrganizationHistory.objects.filter(name=name1).count())
        self.assertEqual(1, Revision.objects.count() - revisions_count_0) # now must have Revision

        self.assertEqual(name1, OrganizationHistory.objects.order_by('-created_at_rev')[0].name)
        self.assertEqual(Revision.objects.order_by('-pk')[0], OrganizationHistory.objects.order_by('-created_at_rev')[0].created_at_rev)
        self.assertEqual(None, OrganizationHistory.objects.order_by('-created_at_rev')[0].obsoleted_at_rev)
        self.assertEqual(None, OrganizationHistory.objects.order_by('-created_at_rev')[0].deleted_at_rev)

        with transaction.atomic():

            logger.debug("now let's change the name and make another version of the same organization")
            name2 = self.tmpnam('foo2')
            logger.debug('1Organization all: %s', Organization.objects.order_by('-pk'))
            logger.debug('1OrganizationHistory all: %s', OrganizationHistory.objects.order_by('-created_at_rev'))
            foo.name=name2
            foo.save()

            self.assertEqual(1, OrganizationHistory.objects.filter(name=name1).count())
            self.assertEqual(0, OrganizationHistory.objects.filter(name=name2).count())
            # change is written to history at commit

        logger.debug('Organization all: %s', Organization.objects.order_by('-pk'))
        logger.debug('OrganizationHistory all: %s', OrganizationHistory.objects.order_by('-created_at_rev'))
        self.assertEqual(name2, OrganizationHistory.objects.order_by('-created_at_rev')[0].name)
        self.assertEqual(1, OrganizationHistory.objects.filter(name=name1).count())
        self.assertEqual(1, OrganizationHistory.objects.filter(name=name2).count())
        foo1 = OrganizationHistory.objects.get(name=name1)
        foo2 = OrganizationHistory.objects.get(name=name2)
        self.assertEqual(foo1.identity_id, foo2.identity_id)
        self.assertEqual(foo1.created_at_rev.pk, foo2.created_at_rev.pk - 1)
        self.assertEqual(foo1.obsoleted_at_rev.pk, foo2.created_at_rev.pk)
        self.assertEqual(None, foo2.obsoleted_at_rev)
        # below assumes nothing else is accessing the database at the same time - may fail
        self.assertEqual(foo1.created_at_rev.pg_transaction_id, foo2.created_at_rev.pg_transaction_id - 1)
        self.assertEqual(None, foo2.deleted_at_rev)
        self.assertEqual(2, OrganizationHistory.objects.filter(identity_id=foo.id).count())

    @log_exceptions
    def test_delete(self):
        '''
        Test setting of deleted_at_rev
        '''
        with transaction.atomic():
            name1=self.tmpnam('n1')
            n1 = Organization.objects.create(name=name1)
            n1.save()
        self.assertEqual(1, OrganizationHistory.objects.filter(name=name1).count())
        self.assertEqual(None, OrganizationHistory.objects.get(name=name1).deleted_at_rev)
        self.assertEqual(None, OrganizationHistory.objects.get(name=name1).obsoleted_at_rev)
        logger.debug('Organization all: %s', Organization.objects.order_by('-pk'))
        logger.debug('OrganizationHistory all: %s', OrganizationHistory.objects.order_by('-created_at_rev'))
        logger.debug('checks done')
        with transaction.atomic():
            n1.delete()
            logger.debug('deleted n1')
            rev = Revision.objects.my
            logger.debug('committing now')
        logger.debug('deletion committed')
        logger.debug('Organization all2: %s', Organization.objects.order_by('-pk'))
        logger.debug('OrganizationHistory all2: %s', OrganizationHistory.objects.order_by('-created_at_rev'))
        self.assertEqual(1, OrganizationHistory.objects.filter(name=name1).count())
        self.assertEqual(rev.id, OrganizationHistory.objects.get(name=name1).deleted_at_rev.id)
        self.assertEqual(rev.id, OrganizationHistory.objects.get(name=name1).obsoleted_at_rev.id)

    @log_exceptions
    def test_multiple_modifications(self):
        '''
        Multiple changes to the same object within the same transaction.
        '''
        with transaction.atomic():
            name1=self.tmpnam('n1')
            name2=self.tmpnam('n2')
            name3=self.tmpnam('n3')
            name4=self.tmpnam('n4')
            n1 = Organization.objects.create(name=name1)
            n1.save()
        self.assertEqual(1, OrganizationHistory.objects.filter(name=name1).count())
        logger.debug('now perform multiple updates')
        with transaction.atomic():
            n1.name=name2
            n1.save()
            Organization.objects.filter(name=name2).update(name=name3)
            Organization.objects.filter(name=name3).update(name=name4)
        logger.debug('Organization all: %s', Organization.objects.order_by('-pk'))
        logger.debug('OrganizationHistory all: %s', OrganizationHistory.objects.order_by('-created_at_rev'))

        self.assertEqual(1, OrganizationHistory.objects.filter(name=name1).count())
        self.assertEqual(0, OrganizationHistory.objects.filter(name=name2).count())
        self.assertEqual(0, OrganizationHistory.objects.filter(name=name3).count())
        self.assertEqual(1, OrganizationHistory.objects.filter(name=name4).count())

    @log_exceptions
    def test_create_and_delete(self):
        '''
        Object is created and immediately deleted within the same transaction.
        '''
        with transaction.atomic():
            name1=self.tmpnam('n1')
            n1 = Organization.objects.create(name=name1)
            n1.save()
            n1.delete()
            logger.debug('Organization all: %s', Organization.objects.order_by('-pk'))
            logger.debug('OrganizationHistory all: %s', OrganizationHistory.objects.order_by('-created_at_rev'))
        self.assertEqual(0, OrganizationHistory.objects.filter(name=name1).count())

    @log_exceptions
    def test_create_modify_and_delete(self):
        '''
        Object is created, then modified and immediately deleted within the same transaction.
        '''
        with transaction.atomic():
            name2=self.tmpnam('n2')
            name3=self.tmpnam('n3')
            n1 = Organization.objects.create(name=name2)
            n1.save()
            n1.name=name3
            n1.save()
            n1.delete()
        self.assertEqual(0, OrganizationHistory.objects.filter(name=name2).count())
        self.assertEqual(0, OrganizationHistory.objects.filter(name=name3).count())

class RevisionTest(HistoryTransactionTestCase):
    @log_exceptions
    def test_head(self):
        '''
        Test that Revision is created at transaction commit.
        '''
        Revision.objects.create_first()
        rev0 = Revision.objects.head
        name1=self.tmpnam('foo')
        with transaction.atomic():
            foo = Organization(name=name1)
            foo.save()
        self.assertEqual(rev0.id+1, Revision.objects.head.id) # assume pg increments sequence by one
        foo_v0 = OrganizationHistory.objects.order_by('-created_at_rev')[0]
        self.assertTrue(foo_v0.created_at_rev.pg_transaction_id != 0)
        self.assertEquals(name1, foo_v0.name)
        self.assertEquals(None, foo_v0.created_at_rev.committer)

    @log_exceptions
    def test_head_multiple_objects(self):
        '''
        Only one Revision must be created at transaction commit even when multiple rows created.
        '''
        Revision.objects.create_first()
        count0 = Revision.objects.count()
        with transaction.atomic():
            n1 = Organization.objects.create(name=self.tmpnam('n1'))
            n2 = Organization.objects.create(name=self.tmpnam('n2'))
            n3 = Organization.objects.create(name=self.tmpnam('n3'))
            Employee.objects.create(first_name=self.tmpnam('e1'), last_name=self.tmpnam('e2'), cost_center=n1)
        self.assertEqual(count0+1, Revision.objects.count())
        with transaction.atomic():
            Organization.objects.create(name=self.tmpnam('n11'))
            Organization.objects.create(name=self.tmpnam('n22'))
        self.assertEqual(count0+2, Revision.objects.count())

    @log_exceptions
    def test_view(self):
        '''
        Test that viewing the database at a given revision works.

        Table of CUD operations performed in this testcase:
             d1   d2   o1   o2
        r0   C    C
        r1   D    U    C
        r2        D         C
        r3
        '''
        Revision.objects.create_first()
        n1 = self.tmpnam('o1')
        n2 = self.tmpnam('o2')
        d1n = self.tmpnam('d1')
        d2n = self.tmpnam('d2')
        d2mod = self.tmpnam('d2mod')

        with transaction.atomic():
            # ... Create some history
            firstRev = Revision.objects.my

        with transaction.atomic():
            d1=Organization.objects.create(name=d1n)
            d2=Organization.objects.create(name=d2n)
            r0=Revision.objects.my

        with transaction.atomic():
            d1_pk = d1.pk
            d1.delete()
            d2.name=d2mod
            d2.save()
            o1=Organization.objects.create(name=n1) # created in an earlier transaction
            r1=Revision.objects.my

        with transaction.atomic():

            d2_pk = d2.pk
            d2.delete()
            o2=Organization.objects.create(name=n2)
            r2=Revision.objects.my

        with transaction.atomic():
            r3=Revision.objects.my

        logger.debug('Organization all: %s', Organization.objects.order_by('-pk'))
        logger.debug('OrganizationHistory all: %s', OrganizationHistory.objects.order_by('-created_at_rev'))

        self.assertEqual(5, OrganizationHistory.objects.filter(name__contains='test_view').count())
        self.assertEqual(0, firstRev.view(OrganizationHistory.objects.filter(name__contains='test_view')).count())
        self.assertEqual(2, r0.view(OrganizationHistory.objects.filter(name__contains='test_view')).count())
        self.assertEqual(2, r1.view(OrganizationHistory.objects.filter(name__contains='test_view')).count())
        self.assertEqual(2, r2.view(OrganizationHistory.objects.filter(name__contains='test_view')).count())
        self.assertEqual(2, r3.view(OrganizationHistory.objects.filter(name__contains='test_view')).count())

        self.assertEqual(1, OrganizationHistory.objects.filter(identity_id=d1_pk).count())
        self.assertEqual(1, r0.view(OrganizationHistory.objects.filter(identity_id=d1_pk)).count())
        self.assertEqual(0, r1.view(OrganizationHistory.objects.filter(identity_id=d1_pk)).count())
        self.assertEqual(0, r2.view(OrganizationHistory.objects.filter(identity_id=d1_pk)).count())
        self.assertEqual(0, r3.view(OrganizationHistory.objects.filter(identity_id=d1_pk)).count())

        self.assertEqual(2, OrganizationHistory.objects.filter(identity_id=d2_pk).count())
        self.assertEqual(1, r0.view(OrganizationHistory.objects.filter(identity_id=d2_pk)).count())
        self.assertEqual(1, r1.view(OrganizationHistory.objects.filter(identity_id=d2_pk)).count())
        self.assertEqual(0, r2.view(OrganizationHistory.objects.filter(identity_id=d2_pk)).count())
        self.assertEqual(0, r3.view(OrganizationHistory.objects.filter(identity_id=d2_pk)).count())

        self.assertEqual(d2n, r0.view(OrganizationHistory.objects.filter(identity_id=d2_pk))[0].name)
        self.assertEqual(d2mod, r1.view(OrganizationHistory.objects.filter(identity_id=d2_pk))[0].name) # changed name must be found in history

        self.assertEqual(0, r0.view(OrganizationHistory.objects.filter(identity_id=o1.pk)).count())
        self.assertEqual(1, r1.view(OrganizationHistory.objects.filter(identity_id=o1.pk)).count())
        self.assertEqual(1, r2.view(OrganizationHistory.objects.filter(identity_id=o1.pk)).count())
        self.assertEqual(1, r3.view(OrganizationHistory.objects.filter(identity_id=o1.pk)).count())

        self.assertEqual(0, r0.view(OrganizationHistory.objects.filter(identity_id=o2.pk)).count())
        self.assertEqual(0, r1.view(OrganizationHistory.objects.filter(identity_id=o2.pk)).count())
        self.assertEqual(1, r2.view(OrganizationHistory.objects.filter(identity_id=o2.pk)).count())
        self.assertEqual(1, r3.view(OrganizationHistory.objects.filter(identity_id=o2.pk)).count())

        logger.debug('test organization with foreign key reference')
        with transaction.atomic():
            bn = self.tmpnam('bar')
            bar = Organization(name=bn, parent_organization=o1)
            bar.save()

        with transaction.atomic():
            bar1 = OrganizationHistory.objects.filter(name=bn)[0]
            self.assertEqual(bar1.parent_organization_id, o1.pk)
            logger.debug('DONE')


class ForeignKeyTest(HistoryTransactionTestCase):
    @log_exceptions
    def test_organization_fk(self):
        '''
        Foreign keys are just like any other field from the history point of view, because
        history is not able to maintain FK constraints.
        '''
        with transaction.atomic():
            foo = Organization(name='foo')
            foo.save()
            logger.debug('create another organization with foreign key reference')
            bar = Organization(name='bar', parent_organization=foo)
            bar.save()


        bar1 = OrganizationHistory.objects.filter(name='bar')[0]
        self.assertEqual(bar1.parent_organization_id, foo.pk)
        logger.debug('DONE')

        # ??? self.assertEqual(, OrganizationHistory.objects.filter(name='foo2').count())
        # now change the BOTH objects in the same transaction and make sure that the FK fields in history point to right place


class ManyToManyTest(HistoryTransactionTestCase):
    '''
    Test that M2M CRUD operations are recorded in the corresponding History table
    '''
    @log_exceptions
    def test_m2m(self):
        with transaction.atomic():
            Revision.objects.create_first()
            r0 = Revision.objects.my

        with transaction.atomic():
            o1 = Organization(name='o1')
            o1.save()
            o2 = Organization(name='o2')
            o2.save()
            e1 = o1.employee_set.create(first_name='e1first', last_name='e1last', cost_center=o2)
            e2 = o1.employee_set.create(first_name='e2first', last_name='e2last', cost_center=o1)
            e3 = o2.employee_set.create(first_name='e3first', last_name='e3last', cost_center=o1)
            r1 = Revision.objects.my



        # all organizations where e1first ever belonged
        all_organizations = EmployeeOrganizationsHistory.objects.filter(employee_id=e1.id).values_list('organization_id', flat=True).order_by('pk')
        self.assertEqual([o1.pk], sorted(set(all_organizations)))

        with transaction.atomic():
            logger.debug('modify m2m: e1 belongs to two organizations')
            e1.organizations.add(o2)
            r2 = Revision.objects.my

        all_organizations = EmployeeOrganizationsHistory.objects.filter(employee_id=e1.id).values_list('organization_id', flat=True).order_by('pk')
        self.assertCountEqual([o1.pk, o2.pk], sorted(set(all_organizations)))

        with transaction.atomic():
            logger.debug('modify m2m: e1 belongs only to o2')
            e1.organizations=[o2]
            e1.save()
            r3 = Revision.objects.my

        all_organizations = EmployeeOrganizationsHistory.objects.filter(employee_id=e1.id).values_list('organization_id', flat=True).order_by('pk')
        self.assertCountEqual([o1.pk, o2.pk], sorted(set(all_organizations)))
        logger.debug('modify m2m: e1 does not belong to any organization anymore')
        with transaction.atomic():
            r4 = Revision.objects.my
            e1.organizations=[]
            e1.save()

        r5 = Revision.objects.my
        all_organizations = EmployeeOrganizationsHistory.objects.filter(employee_id=e1.id).values_list('organization_id', flat=True).order_by('pk')
        self.assertCountEqual([o1.pk, o2.pk], sorted(set(all_organizations)))

        # now verify results for each revision so far
        self.assertCountEqual([], r0.view(EmployeeOrganizationsHistory.objects.filter(employee_id=e1.pk)))
        self.assertCountEqual([], r0.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o1.pk)))

        self.assertCountEqual([o1.pk], [o.organization_id for o in r1.view(EmployeeOrganizationsHistory.objects.filter(employee_id=e1.pk))])
        self.assertCountEqual([e1.pk, e2.pk], [o.employee_id for o in r1.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o1.pk))])
        self.assertCountEqual([e3.pk], [o.employee_id for o in r1.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o2.pk))])

        self.assertCountEqual([o1.pk, o2.pk], [o.organization_id for o in r2.view(EmployeeOrganizationsHistory.objects.filter(employee_id=e1.pk))])
        self.assertCountEqual([e1.pk, e2.pk], [o.employee_id for o in r2.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o1.pk))])
        self.assertCountEqual([e3.pk, e1.pk], [o.employee_id for o in r2.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o2.pk))])

        self.assertCountEqual([o2.pk], [o.organization_id for o in r3.view(EmployeeOrganizationsHistory.objects.filter(employee_id=e1.pk))])
        self.assertCountEqual([e2.pk], [o.employee_id for o in r3.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o1.pk))])
        self.assertCountEqual([e3.pk, e1.pk], [o.employee_id for o in r3.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o2.pk))])

        self.assertCountEqual([], [o.organization_id for o in r4.view(EmployeeOrganizationsHistory.objects.filter(employee_id=e1.pk))])
        self.assertCountEqual([e2.pk], [o.employee_id for o in r4.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o1.pk))])
        self.assertCountEqual([e3.pk], [o.employee_id for o in r4.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o2.pk))])

        self.assertCountEqual([], [o.organization_id for o in r5.view(EmployeeOrganizationsHistory.objects.filter(employee_id=e1.pk))])
        self.assertCountEqual([e2.pk], [o.employee_id for o in r5.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o1.pk))])
        self.assertCountEqual([e3.pk], [o.employee_id for o in r5.view(EmployeeOrganizationsHistory.objects.filter(organization_id=o2.pk))])


class LogCommitterTest(HistoryTransactionTestCase):
    '''
    Test that the the user performing the operation is saved in the database.
    We must explicitly specify the name of the logged-in user, because
    Django applications typically access the database using only one username and password.
    '''
    @log_exceptions
    def test_log_committer(self):
        '''
        Test setting the committer
        '''
        with transaction.atomic():
            Revision.objects.set_current_committer(32)
            rev1 = Revision.objects.my
            name1=self.tmpnam('n1')
            name2=self.tmpnam('n2')
            n1 = Organization.objects.create(name=name1)
            n2 = Organization.objects.create(name=name2)

        with transaction.atomic():
            Revision.objects.set_current_committer(41)
            logger.debug('change committer of existing revision')
            Revision.objects.set_current_committer(42)
            name3=self.tmpnam('n3')
            n3 = Organization.objects.create(name=name3)
            logger.debug('modify object as different committer')
            name4=self.tmpnam('n4')
            n2.name = name4
            n2.save()
            rev2 = Revision.objects.my

        self.assertEqual(32, Revision.objects.get(pk=rev1.id).committer)
        self.assertEqual(42, Revision.objects.get(pk=rev2.id).committer)

        self.assertEqual(rev2.id, OrganizationHistory.objects.get(name=name3).created_at_rev.id)
        self.assertEqual(42, OrganizationHistory.objects.get(name=name3).created_at_rev.committer)
        self.assertEqual(42, OrganizationHistory.objects.get(name=name4).created_at_rev.committer)

        self.assertEqual(rev1.id, OrganizationHistory.objects.get(name=name1).created_at_rev.id)
        self.assertEqual(32, OrganizationHistory.objects.get(name=name1).created_at_rev.committer)
        self.assertEqual(32, OrganizationHistory.objects.get(name=name2).created_at_rev.committer)


class TransHistoryMixinTest(HistoryTransactionTestCase):
    '''
    Test the api provided by TransHistoryMixin
    '''
    @log_exceptions
    def test_mixin(self):
        '''
        '''
        Revision.objects.create_first()

        with transaction.atomic():

            name_v1 = self.tmpnam('e1')
            name_v2 = self.tmpnam('e2')
            name_v3 = self.tmpnam('e3')
            organization_v1 = Organization.objects.create(name=self.tmpnam('n1'))
            organization_v2 = None
            organization_v3 = Organization.objects.create(name=self.tmpnam('n3'))
            cc = Organization.objects.create(name=self.tmpnam('n4'))

            Employee.objects.create(first_name=name_v1, last_name=self.tmpnam('e2'), cost_center=cc, primary_organization=organization_v1)
            r1 = Revision.objects.my

        with transaction.atomic():
            Employee.objects.filter(first_name=name_v1).update(first_name=name_v2, primary_organization=None)
            r2 = Revision.objects.my

        with transaction.atomic():
            Employee.objects.filter(first_name=name_v2).update(first_name=name_v3, primary_organization=organization_v3)
            r3 = Revision.objects.my

        emp = Employee.objects.get(first_name=name_v3)
        self.assertEqual(name_v1, emp.get_old_version(r1.pk).first_name)
        self.assertEqual(organization_v1.pk, emp.get_old_version(r1.pk).primary_organization_id)
        self.assertEqual(name_v2, emp.get_old_version(r2.pk).first_name)
        self.assertEqual(None, emp.get_old_version(r2.pk).primary_organization_id)
        self.assertEqual(name_v3, emp.get_old_version(r3.pk).first_name)
        self.assertEqual(organization_v3.pk, emp.get_old_version(r3.pk).primary_organization_id)
