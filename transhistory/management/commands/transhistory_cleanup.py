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
from optparse import make_option

from django import VERSION
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import models
from django.db import transaction
from django.db import connection
from django.db.utils import DatabaseError

from transhistory.history_db import delete_empty_revisions_2
from transhistory.models import Revision
from symbol import varargslist

class Command(BaseCommand):
    '''
    Command for (un)installing django-trans-history stored procedures
    '''
    '''
    option_list = BaseCommand.option_list + (
        make_option('--range-start',
            dest='range_start',
            metavar='ID',
            type=int,
            help='start processing at revision ID (inclusive)'),
        make_option('--range-end',
            dest='range_end',
            metavar='ID',
            type=int,
            help='end processing at revision ID (non-inclusive)'),
        make_option('--num-revisions',
            dest='num_revisions',
            metavar='N',
            type=int,
            help='clean up at most N revisions'),
        make_option('--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='Do not actually perform any changes'),
        make_option('--verbose',
            action='store_true',
            dest='verbose',
            default=False,
            help='More verbose output'),
        make_option('--only-older-than',
            dest='only_older_than',
            type=int,
            metavar='SECONDS',
            help='only delete revisions older than specified number of seconds'),
        make_option('--refcounts-file',
            dest='refcounts_file',
            metavar='FILE',
            help='save refcounts to file'),

    )
    '''
    help = 'Clean up non-referenced revision objects from the database'

    def handle(self, *args, **options):
        if options.get('verbose'):
            self.stdout.write('Start cleanup...\n')
        raise Exception('todo: rewrite using add_arguments')
        '''
        qs = Revision.objects.all().order_by('pk')

        range_start = options.get('range_start')
        if range_start:
            qs = qs.filter(id__gte=range_start)

        range_end = options.get('range_end')
        if range_end:
            qs = qs.filter(id__lt=range_end)

        num_revisions = options.get('num_revisions')
        if num_revisions:
            qs = qs[:num_revisions]
        '''
        delete_empty_revisions_2(options.get('range_start'),
                                 options.get('range_end'),
                                 options.get('num_revisions'),
                                 options.get('only_older_than'),
                                 options.get('dry_run'),
                                 options.get('refcounts_file'),
                                 options.get('verbose'))
        if options.get('verbose'):
            self.stdout.write('Clean-up complete.\n')


