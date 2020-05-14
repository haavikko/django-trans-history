# -*- coding: utf-8 -*-
'''
Created on Apr 25, 2011

@author: mhaa

Tools for installing the database procedures.
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import *
from django.db import connection
from django.db import transaction
from django.apps import apps
import logging
logger = logging.getLogger(__name__)
from transhistory import models
from transhistory import history_db
from transhistory import backend

__all__ = ['transhistory_install', 'transhistory_uninstall']



@transaction.atomic
def transhistory_install(models=None):
    '''
    (re)install the history tracking procedures in the database.
    '''
    tables = connection.introspection.table_names()
    # sorted to make deterministic, actual ordering does not matter
    seen_models = sorted(connection.introspection.installed_models(tables), key=lambda cls: (cls.__module__, cls.__name__))
    if models:
        raise Exception('not yet supported')
        models = [apps.get_model(*m.split('.', 1)) for m in models]
        for m in models:
            if m not in seen_models:
                raise Exception('Model not found in installed_models: %s' % m)
        seen_models = models
    db_backend = backend.get_history_backend()

    for m in seen_models:
        # heuristics for determining that this is indeed a transhistory model
        # in case an existing model ends with 'History', also check for existence of 'created_at_rev'
        if m.__name__.endswith('History') and hasattr(m, 'created_at_rev'):

            target_model = history_db.get_target_model(m)

            if hasattr(target_model, 'TransHistory') and getattr(target_model.TransHistory, 'is_m2m_model'):
                logger.debug('target model %s is a m2m model, the m2m relation is handled when the class containing m2m field is processed', m.__name__)
                continue

            if not target_model:
                logger.debug('target model for %s not found, this is ok in case of many-to-many intermediary table', m.__name__)
                continue

            logger.debug('installing history bindings: %s %s', target_model, m)
            db_backend.install_history_bindings(target_model, m)

    #logger.debug('models: %s', [(type(m), m) for m in seen_models])
    #history_models = sorted([m for m in seen_models if m == models.HistoryModel])
    #logger.debug('models: %s', history_models)


#def _get_pg_

@transaction.atomic
def transhistory_uninstall():
    '''
    TODO: uninstall all history management procedures from the database.
    Uninstall procedures also for tables whose model does not exist anymore.
    '''
    raise Exception('Not Implemented')

