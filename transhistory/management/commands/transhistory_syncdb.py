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

from transhistory.syncdb import transhistory_install, transhistory_uninstall
from transhistory.models import Revision
from symbol import varargslist
# for more, see e.g.
# https://github.com/etianen/django-reversion/blob/master/src/reversion/management/commands/createinitialrevisions.py


def vararg_callback(option, opt_str, value, parser):
    # based on: http://docs.python.org/2/library/optparse.html#callback-example-6-variable-arguments
    # optparse (used by django) does not support nargs='+' like argparse does
    assert value is None
    value = []
    for arg in parser.rargs:
        # stop on --foo like options
        if arg[:2] == "--" and len(arg) > 2:
            break
        # stop on -f like options
        if arg[:1] == "-" and len(arg) > 1:
            break
        value.append(arg)

    del parser.rargs[:len(value)]
    setattr(parser.values, option.dest, value)


class Command(BaseCommand):
    '''
    Command for (un)installing django-trans-history stored procedures
    '''

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--models',
            nargs='+',
            help = "models (requires transhistory configuration in model class)",
            metavar = "MODEL..."
        )
        parser.add_argument(
            '--uninstall',
            action='store_true',
            help='Uninstall trans-history procedures instead of (re)installing them',
        )

    def _init_plpgsql(self):
        cursor = connection.cursor()

        cursor.execute("SELECT 1 FROM pg_catalog.pg_language WHERE lanname='plpgsql'");
        if not cursor.fetchall():
            try:
                cursor.execute('CREATE LANGUAGE plpgsql;')
            except DatabaseError:
                self.stderr.write('Error executing sql "CREATE LANGUAGE plpgsql;", please create plpgsql language manually in your database before continuing. Most common reason for this error is insufficient permissions.\n')
                return False
        return True

    def handle(self, *args, **options):
        if options["uninstall"]:
            raise CommandError('Not implemented')
            transhistory_uninstall()
        else:
            self.stdout.write('Installing...\n')
            if self._init_plpgsql():
                with transaction.atomic():
                    models = options.get('models')
                    transhistory_install(models)
                    Revision.objects.create_first()
                    self.stdout.write('Installed trans-history. This command needs to be re-run if you modify your history models or transhistory version changes.\n')


