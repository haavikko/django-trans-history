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

from django.contrib.auth.models import User
from transhistory.models import Revision
from personnel.models import *

from transhistory.test_util import HistoryTransactionTestCase, log_exceptions

import logging
logger = logging.getLogger(__name__)

class DjangoAuthUserTest(HistoryTransactionTestCase):
    '''
    Test that the the user performing the operation is saved in the database.
    We must explicitly specify the name of the logged-in user, because
    Django applications typically access the database using only one username and password.
    '''
    @log_exceptions
    def test_user_history(self):
        '''
        Test history creating and modifying a django.contrib.auth.User
        '''
        with transaction.atomic():
            Revision.objects.create_first()
            r0 = Revision.objects.my

        with transaction.atomic():
            r1 = Revision.objects.my
            u1 = User.objects.create_user('user1', 'user1@example.com')

        with transaction.atomic():
            r2 = Revision.objects.my
            u2 = User.objects.create_user('user2', 'user2@example.com')
            User.objects.filter(username='user1').update(first_name='xyz', last_name='foo', username='bar', email='aaa@example.com')
            u1.set_password('xyz')

        logger.debug('User all pre-delete: %s', User.objects.order_by('-pk'))

        with transaction.atomic():
            r3 = Revision.objects.my
            User.objects.filter(pk__in=[u1.pk, u2.pk]).delete()

        logger.debug('User all post-delete: %s', User.objects.order_by('-pk'))
        logger.debug('UserHistory all: %s', UserHistory.objects.order_by('-pk'))

        self.assertEqual(2, UserHistory.objects.filter(identity_id=u1.pk).count())
        self.assertEqual('user1', r1.view(UserHistory.objects.filter(identity_id=u1.pk))[0].username)
        self.assertEqual('', r1.view(UserHistory.objects.filter(identity_id=u1.pk))[0].first_name)
        self.assertEqual('user1@example.com', r1.view(UserHistory.objects.filter(identity_id=u1.pk))[0].email)
        self.assertEqual('bar', r2.view(UserHistory.objects.filter(identity_id=u1.pk))[0].username)
        self.assertEqual('xyz', r2.view(UserHistory.objects.filter(identity_id=u1.pk))[0].first_name)
        self.assertEqual('aaa@example.com', r2.view(UserHistory.objects.filter(identity_id=u1.pk))[0].email)

        self.assertEqual(0, r0.view(UserHistory.objects.all()).count())
        self.assertEqual(1, r1.view(UserHistory.objects.all()).count())
        self.assertEqual(2, r2.view(UserHistory.objects.all()).count())
        self.assertEqual(0, r3.view(UserHistory.objects.all()).count())


