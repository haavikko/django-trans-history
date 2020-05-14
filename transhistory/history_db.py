# -*- coding: utf-8 -*-
'''
Created on Apr 26, 2011

@author: mhaa

Common internal utilities

'''
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
from future.utils import raise_
import itertools
import datetime
import string
import logging

import transhistory

from django.apps import apps
from django.db.transaction import atomic
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
import collections

logger = logging.getLogger(__name__)

def get_param(model, param_name, default_value=None):
    '''
    Get parameter from the TransHistory inner class
    '''
    if hasattr(model, 'TransHistory'):
        return getattr(model.TransHistory, param_name, default_value)

def get_history_fields(model):
    '''
    Determine which fields in model should be stored in the history model.

    returns: list of Field objects

    * history_model is expected to have fields with the same name
    * TODO: support for TransHistory.fields
    '''
    ret = [f for f in model._meta.fields]
    return ret

def get_m2m_history_fields(model, history_model):
    '''
    Determine which m2m fields need to be managed by trans-history.
    NOTE: GenericRelation fields do not count as actual m2m fields, although Django lists them in model._meta.many_to_many.
    '''
    ret = [f for f in model._meta.many_to_many if not isinstance(f, GenericRelation)]
    if get_param(history_model, 'm2m_fields'):
        # filter out
        ret = [f for f in ret if f.name in get_param(history_model, 'm2m_fields')]
    return ret

def get_pk_field(model):
    for f in model._meta.fields:
        if f.primary_key:
            return f

def get_target_model(history_model):
    # by default target model is in same app
    # in case of m2m field, there is usually no corresponding Django model, so None is returned.
    # However if a m2m model class is defined (typically with "managed=False" in Meta), it can be used.
    # if get_target_model does not find the model, check that app_label is set correctly in target model.
    target_app = history_model._meta.app_label
    hist_config = getattr(history_model, 'TransHistory', None)

    # remove 'History' from end of model name
    target_model_name = history_model.__name__[0:-len('History')]
    if hist_config:
        # need to track history in another app
        target_app = getattr(history_model.TransHistory, 'target_app_label', target_app)
        if hasattr(hist_config, 'target_model'):
            target_model_name = hist_config.target_model

    logger.debug('get_target_model: m=%s, %s, %s.%s', history_model, history_model.__name__, target_app, target_model_name)
    try:
        return apps.get_model(target_app, target_model_name)
    except LookupError as e:
        logger.debug('LookupError: %s', e)
        return None

# optimization for get_history_model
_history_model_cache = {}

def get_history_model(model):
    '''
    find history model even in different app
    '''
    if model in _history_model_cache:
        return _history_model_cache[model]
    ret = None
    hist_config = getattr(model, 'TransHistory', None)
    for app_label in list(apps.app_configs.keys()): # 1.11 change
        if hist_config:
            try:
                ret = apps.get_model(app_label, getattr(hist_config, 'history_model', model.__name__ + 'History'))
            except LookupError:
                pass
        else:
            try:
                ret = apps.get_model(app_label, model.__name__ + 'History')
            except LookupError:
                pass
        if ret:
            break
    _history_model_cache[model] = ret
    return ret

def get_m2m_history_model(m2m_field, history_app_label):
    # default naming convention:
    # model1 + model2 + relation name with 1st letter and every letter after '_' capitalized + 'History'
    # (so that we can support multiple m2m relations between models)

    # hist_config = getattr(m2m_field.model, 'TransHistory', None)

    # NOTE: m2m_field.rel.to.__name__ is not part of history model name because model+field+'History' is unique identification

    relation_name_with_caps = ''.join([string.capwords(s) for s in m2m_field.name.split('_')])

    model_name = '%s%sHistory' % (m2m_field.model.__name__, relation_name_with_caps)

    #ret = apps.get_model(m2m_field.model._meta.app_label, getattr(hist_config, 'm2m_history_model_%s' % m2m_field.name, def_val))
    logger.debug('get_m2m_history_model %s %s', history_app_label, model_name)
    ret = apps.get_model(history_app_label, model_name)

    if not ret:
        raise_(Exception, 'No history model for m2m field %s. Expected to find model %s. Please either define history model or define m2m_fields without this field in TransHistory config in %s' % (m2m_field.name, model_name, m2m_field.model.__name__,))
    return ret

def get_app_label(app):
    """
    """
    return app.__name__.split('.')[-2]

def delete_empty_revisions(revisions=None, dry_run=True, verbose=True, plain_delete=True, max_run_time=None, chunksize=1000, start_from=0, only_older_than=60*60*48):
    # note:
    # when Django creates foreign keys in Postgres, it does not specify CASCADE option,
    # so it defaults to "restrict". In case there is a model that Django no longer knows
    # about, you may get an error on foreign key violation.
    # (TODO: check what kind of exception is thrown, and log them, as those cases
    # should not stop the process)
    from django.db import IntegrityError
    from django.db import connection
    start_time = datetime.datetime.now()

    REV_CHUNK_SIZE = chunksize or 1000
    # delete revisions that do not have any objects corresponding to them in the database.
    if revisions is None:
        revisions = transhistory.models.Revision.objects.all().order_by('pk').iterator()
    if only_older_than:
        limit = start_time - datetime.timedelta(seconds=only_older_than)
        # slows down a lot revisions = revisions.filter(committed_at__lte=limit)

    first_rev = transhistory.models.Revision.objects.all().order_by('pk')[0]
    empty_revisions = []

    latest_entry = start_from or 0
    n_checked = 0
    n_empty = 0
    while True:
        # manage huge querysets
        chunck_start = datetime.datetime.now()
        rev_chunk = revisions[latest_entry:latest_entry+REV_CHUNK_SIZE]
        if not rev_chunk:
            break
        if verbose:
            print('chunk %s:%s' % (latest_entry, latest_entry + REV_CHUNK_SIZE))
        latest_entry += REV_CHUNK_SIZE
        n_checked += REV_CHUNK_SIZE
        #if group_delete:
        #    try:
        #        rev_ids = tuple(r.pk for r in rev_chunk)
        #        with atomic():
        #            c = connection.cursor()
        #            c.execute('DELETE FROM transhistory_revision WHERE id IN %s', [rev_ids])
        #    except IntegrityError:
        #        print 'not empty %s - %s' % (rev_ids[0], rev_ids[-1])
        #    else:
        #        print 'empty %s - %s' % (rev_ids[0], rev_ids[-1])
        #else:
        for rev in rev_chunk:
            # do not delete recent enough revisions (a revision id might be stored e.g.
            # in a cache, and should be kept)
            if rev.committed_at > start_time - datetime.timedelta(seconds=only_older_than):
                continue
            # preserve zero revision even if empty to ensure that one revision always remains
            if rev == first_rev:
                continue
            if plain_delete:
                # do not go through the motions of trying to find related objects, instead
                # try deleting the revision and rely on database integrity check.
                # this method requires that ON DELETE CASCADE is not set in foreign keys.
                # (or if it is set, then must not )
                try:
                    with atomic():
                        c = connection.cursor()
                        c.execute('DELETE FROM transhistory_revision WHERE id=%s', [rev.pk])
                except IntegrityError:
                    if verbose:
                        print('not empty %s' % rev.pk)
                else:
                    if verbose:
                        print('empty %s' % rev.pk)
                    n_empty += 1
            else:
                # disabled, too slow
                '''
                rel_objs = itertools.chain(*[getattr(rev, rel.get_accessor_name()).all() for
                                             rel in rev._meta.get_all_related_objects()])
                try:
                    rel_objs.next()
                    if verbose:
                        print 'not empty %s' % rev
                except StopIteration:
                    # it was empty
                    if verbose:
                        print 'empty %s' % rev
                    empty_revisions.append(rev.pk)
                    if not dry_run:
                        rev.delete()
                else:
                    continue
                '''
        elapsed_from_start = datetime.datetime.now() - start_time
        if verbose:
            elapsed = datetime.datetime.now() - chunck_start
            print('elapsed: %s, from start %s, checked %s, of which %s removed' % (elapsed, elapsed_from_start, n_checked, n_empty))
        if max_run_time and elapsed_from_start > max_run_time:
            print('max_run_time reached, checked %s, of which %s removed' % (n_checked, n_empty))
            break

    print('total: %s' % (datetime.datetime.now() - start_time))
    return empty_revisions


def delete_empty_revisions_2(range_start, range_end, num_revisions, only_older_than=60*60*48, dry_run=True, refcounts_file=None, verbose=True, delete=False, print_empty=False):
    # refcounts_file: save to file revisions with refcount > 0
    data = get_refcounts(range_start, range_end, True if delete or print_empty else False, verbose)

    recent_revs = set()
    if only_older_than:
        recent_revs = set(transhistory.models.Revision.objects.filter(created_at__gte=datetime.datetime.now() - datetime.timedelta(seconds=only_older_than)).values_list('id'))
        if verbose:
            print('%s recent revisions will not be included' % len(recent_revs))

    if delete:
        empty_revs = set([d for d in data if data[d] == 0])
        print('%d empty revisions' % len(empty_revs))
        if only_older_than:
            empty_revs = [r for r in empty_revs if r not in recent_revs]
            print('%d non-recent empty revisions' % len(empty_revs))
        if num_revisions:
            empty_revs = sorted(empty_revs)[:num_revisions]
            print('empty revisions capped at %d' % len(empty_revs))
        if dry_run:
            print('dry run, nothing done')
        else:
            transhistory.models.Revision.objects.filter(pk__in=empty_revs).delete()

    if refcounts_file:
        if verbose:
            print('saving %s revisions with refcount to %s' % (len(data), refcounts_file))
        with open(refcounts_file, 'wb') as f:
            for idx, k in enumerate(data.keys()):
                if verbose and len(data) > 100 and idx % (len(data) // 100) == 0:
                    print('.', end=' ')
                if data[k] > 0 and k not in recent_revs:
                    f.write('%d\n' % k)
    if print_empty:
        print('empty revs:')
        for k in empty_revs:
            print(k)

def get_refcounts(range_start=None, range_end=None, include_non_referenced=False, verbose=False):
    '''
    Count the number of foreign keys referencing each revision.
    Steps:
    * Find all foreign keys referencing transhistory_revision
    * Query all these tables
    * Return dict where revision_id is mapped to number of referencing rows.
    * Only revision_ids that actually actually exist are returned.
    '''
    from django.db import connection
    c = connection.cursor()
    # find referencing tables
    c.execute('''SELECT tc.table_schema, tc.constraint_name, tc.table_name, kcu.column_name, ccu.table_name
AS foreign_table_name, ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE constraint_type = 'FOREIGN KEY'
AND ccu.table_name='transhistory_revision';''')
    rows = sorted(c.fetchall())
    refcounts = collections.defaultdict(int)
    # initialize all existing revisions at 0 if range is used
    if include_non_referenced:
        for rev_id in _get_server_side_refcount_cursor('transhistory_revision', 'id', range_start, range_end, verbose):
            refcounts[rev_id] = 0
    for schema, constraint, table, column, th_table, th_id in rows:
        if th_table != 'transhistory_revision' or th_id != 'id':
            continue
        # print locals()
        with atomic(): # keep transaction short
            ref_cursor = _get_server_side_refcount_cursor(table, column, range_start, range_end, verbose)
            refs_pre = len(refcounts)
            counter = 0
            for rev_id in ref_cursor:
                if rev_id[0] is None:
                    continue
                refcounts[rev_id[0]] += 1
                counter += 1

            if verbose:
                new_refs = len(refcounts) - refs_pre
                if counter or new_refs:
                    print('found %s refs of which %s new in %s.%s' % (counter, new_refs, table, column))

    return refcounts

def _get_server_side_refcount_cursor(table, column, range_start, range_end, verbose=False):
    # use server-side cursor to handle very large data sets
    # ... we already called connection.cursor() once so lazy db connection by django is already done
    from django.db import connection
    cur_name = ('transhistory-get-refcounts-%s-%s' % (table, column))[:70]
    ref_cursor = connection.connection.cursor(name=cur_name)
    # ... see: http://stackoverflow.com/questions/27289957/pass-column-name-as-parameter-to-postgresql-using-psycopg2
    if verbose:
        print('check %s.%s' % (table, column))
    if range_start or range_end:
        sql = '''SELECT %s from %s where %s''' % (column, table, column) + ' BETWEEN %s and %s'
        ref_cursor.execute(sql, (range_start, range_end-1))
    else:
        #print 'X%sX X%sX' % (column, table)
        ref_cursor.execute('SELECT %s from %s' % (column, table))
    return ref_cursor
