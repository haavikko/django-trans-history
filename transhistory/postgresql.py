# -*- coding: utf-8 -*-
'''
Created on Apr 26, 2011

@author: mhaa

Postgresql-specific database backend

note on txid:
Jasen Betts <jasen(at)xnet(dot)co(dot)nz> writes:
> On 2012-06-26, Vlad Arkhipov <arhipov(at)dc(dot)baikal(dot)ru> wrote:
>> Is it guaranteed that if txid2 > txid1 then current_timestamp in
>> transaction 2 >= current_timestamp in transaction 1?

> no.

To enlarge on that: current_timestamp is set at the moment of receipt
from the client of a transaction's first command.  XID is not set until
(and unless) the transaction does something that modifies the database.
The elapsed time between can be quite variable depending on what
commands the client issues.

Even if this weren't the case, I wouldn't recommend relying on such an
assumption, because of factors like clock skew between different
processors.

            regards, tom lane
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import *
import logging
import re

from django.db import connection, transaction
from django.template import Context, Template
from django.conf import settings
from psycopg2.extensions import AsIs

from transhistory import models
from transhistory import history_db
from transhistory import backend
from django.utils.safestring import mark_safe

from transhistory import test_util

logger = logging.getLogger(__name__)

# SQL templates are rendered with Django template engine.
#
# NOTE: if using % in sql sent to psycopg2, must quote it as %% if passing parameters to execute() at the same time
# see http://stackoverflow.com/questions/1734814/why-isnt-psycopg2-executing-any-of-my-sql-functions-indexerror-tuple-index-ou

# Common code that is installed before triggers:
_pg_common = '''
CREATE OR REPLACE FUNCTION foo() RETURNS trigger AS $PROC$
    DECLARE
        revision_id BIGINT := NULL;
        obsoleted_at_rev BIGINT := NULL;
        transaction_id BIGINT := NULL;
    BEGIN
        SELECT INTO revision_id id FROM transhistory_revision WHERE pg_transaction_id = transaction_id;
        IF NOT FOUND THEN
            PERFORM trans_history_logger('New revision');
            INSERT INTO transhistory_revision VALUES(DEFAULT, transaction_id, now(), statement_timestamp(), NULL) RETURNING id INTO revision_id;
        END IF;
        RETURN revision_id;
    END;
$PROC$ LANGUAGE plpgsql VOLATILE;
'''

# TODO: automatic handling of database dump restore
# - on the 1st request, check if current tx_id is less than any other tx_id in the database, and if so, set all existing revision.pg_transaction_id to 0
_pg_trigger_function_template = '''
CREATE OR REPLACE FUNCTION trans_history_trigger_function_{{ table_name }}() RETURNS trigger AS $PROC$
    DECLARE
        created_at_rev BIGINT := NULL;
        obsoleted_at_rev BIGINT := NULL;
        deleted_at_rev BIGINT := NULL;
        transaction_id BIGINT := NULL;
        rows_changed BIGINT := NULL;
        curtime timestamp := now();
        was_found BOOLEAN := false;
    BEGIN
        raise NOTICE 'trans_history_trigger_function_{{ table_name }} start';

        -- find out current transaction id
        SELECT txid_current() INTO transaction_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION '%', 'transaction id not found';
        END IF;
        raise NOTICE 'trans_history_trigger_function_{{ table_name }} txid_current %', transaction_id;
        -- check if a Revision exists for this transaction_id
        -- NOTE: transaction id is only unique within one postgres instance,
        --       so in case database dump is moved to another server,
        --       duplicates may occur. For this reason pg_transaction_id column
        --       must be reset to 0 when restoring dump on another postgres instance.
        -- now() returns start time of current transaction.
        -- statement_timestamp() returns time of current statement
        SELECT INTO created_at_rev id FROM transhistory_revision WHERE pg_transaction_id = transaction_id;
        IF NOT FOUND THEN
            raise NOTICE 'new revision tx=%', transaction_id;
            INSERT INTO transhistory_revision VALUES(DEFAULT, transaction_id, now(), statement_timestamp(), NULL) RETURNING id INTO created_at_rev;
        END IF;
        raise NOTICE 'using revision %', created_at_rev;

        IF (TG_OP = 'INSERT') THEN
            PERFORM trans_history_logger('New entry in {{ history_table_name }}');
            INSERT INTO {{ history_table_name }} ({{ history_table_column_names }}) VALUES({{ history_values }});
            -- no need to set any obsoleted_at_rev to NULL because row was added now.
            -- here assuming that the primary key values are never repeated - it would break history anyway.
        ELSIF (TG_OP = 'UPDATE') THEN
            -- update previous history entry

            -- NOTE: handling of special case where the updated row was created or updated before in the same transaction:
            -- * Leave only one row in history table, showing the latest state.
            -- NOTE: handling of special case where the updated row was created before in the same transaction:
            -- * Leave only one row in history table, showing the latest state.

            PERFORM trans_history_logger('Update previous entry in {{ history_table_name }}');
            -- start with cleaning up any history changes that were made earlier in the same transaction, because
            -- the update operation just made them moot (NOTE: could optimize here!)
            DELETE FROM {{ history_table_name }} WHERE "created_at_rev_id" = created_at_rev AND "identity_id" = NEW.{{ pk_column_name }};
            IF FOUND THEN
                was_found = true;
            END IF;
            UPDATE {{ history_table_name }} SET "obsoleted_at_rev_id" = created_at_rev WHERE "obsoleted_at_rev_id" IS NULL AND "identity_id" = NEW.{{ pk_column_name }};
            GET DIAGNOSTICS rows_changed = ROW_COUNT;
            IF (rows_changed = 0 and was_found) THEN
                PERFORM trans_history_logger('Row created/modified multiple times within the same transaction');
            ELSIF (rows_changed != 1) THEN
                PERFORM trans_history_logger('update on previously un-managed row');
                -- no error, row may be created before transhistory was installed on this table
                -- WAS: RAISE EXCEPTION 'UPDATE {{ history_table_name }} ERROR 48032479: internal error or history table corrupted %', rows_changed;
            END IF;
            PERFORM trans_history_logger('Add updated entry in {{ history_table_name }}');
            INSERT INTO {{ history_table_name }} ({{ history_table_column_names }}) VALUES({{ history_values }});
        ELSIF (TG_OP = 'DELETE') THEN
            -- created_at_rev becomes deleted_at_rev. No new row is added to history table.
            -- NOTE: handling of special case where the deleted row was created in the same transaction:
            -- * As far as the history is concerned, nothing happened because no other transaction had the chance to see it
            -- * Remove all references to this row from the history, do not record the delete operation.
            -- NOTE: handling of special case where the deleted row was modified before in the same transaction:
            -- * As far as the history is concerned, nothing happened because no other transaction had the chance to see it
            --   (assuming at least READ_COMMITTED transaction isolation)
            -- * Remove all previous changes made in the same transaction and record the delete operation.
            -- NOTE: handling of special case when the history deleted row does not exist in history table
            --   (e.g. row was created before history management was installed):
            --   ignore missing rows in history table

            PERFORM trans_history_logger('Record object deletion into {{ history_table_name }}');
            raise NOTICE 'deleted row pk %', OLD.{{ pk_column_name }};
            -- start with cleaning up any history changes that were made earlier in the same transaction, because
            -- the delete operation just made them moot. NOTE: must use OLD instead of NEW here.
            DELETE FROM {{ history_table_name }} WHERE "created_at_rev_id" = created_at_rev AND "identity_id" = OLD.{{ pk_column_name }};
            IF FOUND THEN
                was_found = true;
            END IF;

            UPDATE {{ history_table_name }} SET "obsoleted_at_rev_id" = created_at_rev WHERE "obsoleted_at_rev_id" IS NULL AND "identity_id" = OLD.{{ pk_column_name }};
            GET DIAGNOSTICS rows_changed = ROW_COUNT;
            IF (rows_changed = 1) THEN
                -- default case
                -- deleted_at_rev is redundant but makes querying history data faster at extra cost on delete.
                UPDATE {{ history_table_name }} SET deleted_at_rev_id = created_at_rev WHERE identity_id = OLD.{{ pk_column_name }};
                IF NOT FOUND THEN
                    PERFORM trans_history_logger('ERROR 3740342');
                    RAISE EXCEPTION 'DELETE {{ history_table_name }} ERROR 3740342: internal error or history table corrupted';
                END IF;
            ELSIF (was_found AND rows_changed = 0) THEN
                -- If no row was updated, then we know that the row was created and deleted within the same transaction, so we do not record the deletion either.
                PERFORM trans_history_logger('Object created and deleted within the same transaction, skip history');
            ELSE
                PERFORM trans_history_logger('delete on previously un-managed row');
                -- no error, row may be created before transhistory was installed on this table
                -- RAISE EXCEPTION 'DELETE {{ history_table_name }} ERROR 8234893: internal error or history table corrupted %', rows_changed;
            END IF;
        END IF;

        -- TODO: multiple updates to the same row in one transaction?
        -- raise NOTICE '%', 'trans_history_trigger_function_{{ table_name }} exit';
        raise NOTICE 'trans_history_trigger_function_{{ table_name }} exit txid_current %', transaction_id;
        RETURN NULL; -- result is ignored since this is an AFTER trigger
    END;
$PROC$ LANGUAGE plpgsql VOLATILE;
'''

_pg_trigger_template = '''
DROP TRIGGER IF EXISTS trans_history_trigger_{{ table_name }} on {{ table_name }};

CREATE CONSTRAINT TRIGGER trans_history_trigger_{{ table_name }}
  AFTER UPDATE OR INSERT OR DELETE
  ON {{ table_name }}
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  EXECUTE PROCEDURE trans_history_trigger_function_{{ table_name }}({{ trigger_args }}); /* arguments are passed to trigger function. */
'''

#_internal_history_fields = ['vid', 'identity_id', 'created_at_rev', 'obsoleted_at_rev']

class PostgresHistoryBackend(backend.HistoryBackend):
    '''
    Code specific to handling Postgres database
    '''
    db_logging_enabled = False # TODO: make configurable, now switched on in tests

    def install_history_bindings(self, model, history_model):
        self._pg_install_log_util()
        self._pg_create_trigger_function(model, history_model)
        self._pg_create_trigger_on_table(model._meta.db_table)

        for m2m_field in history_db.get_m2m_history_fields(model, history_model):
            self._pg_create_m2m_trigger_function(m2m_field, history_model._meta.app_label)
            self._pg_create_trigger_on_table(m2m_field.m2m_db_table())

    def uninstall_history_bindings(self, model, history_model):
        # tbd
        pass

    history_table_base_column_names =['vid',
                                      'identity_id',
                                      'created_at_rev_id',
                                      'obsoleted_at_rev_id',
                                      'deleted_at_rev_id',
                                      ]

    @classmethod
    def get_history_table_column_names_string(cls, extra_column_names):
        history_table_column_names = cls.history_table_base_column_names + extra_column_names
        return ', '.join(['"' + name + '"' for name in history_table_column_names])

    def _pg_create_m2m_trigger_function(self, m2m_field, history_app_label):
        '''
        NOTE: The history model for a m2m field must be tracked in the same app as the history for the model defining
        the m2m relation.
        '''
        pk_column_name = 'id' # always on django-created m2m tables
        db_table = m2m_field.m2m_db_table()
        history_model = history_db.get_m2m_history_model(m2m_field, history_app_label)

        logger.debug('install m2m trigger for %s %s %s', m2m_field.name, db_table, history_model)
        # note - there is no "m2m_reverse_column_name" available (as of django 1.3) so just appending "_id" to reverse_field_name.
        history_values = 'DEFAULT, NEW.%s, created_at_rev, obsoleted_at_rev, deleted_at_rev, NEW.%s, NEW.%s_id' % (pk_column_name,
                                                                                                        m2m_field.m2m_column_name(),
                                                                                                        m2m_field.m2m_reverse_field_name())
        column_names = self.get_history_table_column_names_string([
                                        m2m_field.m2m_column_name(),
                                        m2m_field.m2m_reverse_name(),
                                    ])
        self._pg_install_trigger_function(db_table, pk_column_name, history_model._meta.db_table, history_values, column_names)

    def _pg_create_trigger_function(self, model, history_model):
        '''
        replaces any existing trigger function for this model.
        '''
        fields = history_db.get_history_fields(model)
        pk_column_name = history_db.get_pk_field(model).column
        # first values are the internal management fields:
        # vid, identity_id, created_at_rev, obsoleted_at_rev
        history_values = 'DEFAULT, NEW.%(pk_column_name)s, created_at_rev, obsoleted_at_rev, deleted_at_rev' % locals()
        field_values = ', '.join(['NEW."%s"' % f.column for f in fields if f.column != pk_column_name])
        if field_values:
            # field_values is empty if model only has primary key field
            history_values += ', ' + field_values

        column_names = self.get_history_table_column_names_string([f.column for f in fields if f.column != pk_column_name])

        self._pg_install_trigger_function(model._meta.db_table, pk_column_name, history_model._meta.db_table, history_values, column_names)

    def _pg_quote_by_version(self, template):
        # https://docs.djangoproject.com/en/dev/topics/db/sql/:
        #        Note that if you want to include literal percent signs in the query, you have to double them in the case you are passing parameters:
        import psycopg2
        import re



        # in some versions, must use single % instead of %% in procedure definition
        if getattr(settings, 'TRANSHISTORY_DOUBLE_PERCENT', '') == 'never':
            return template
        if getattr(settings, 'TRANSHISTORY_DOUBLE_PERCENT', '') == 'always' or\
            any([ver in psycopg2.__version__ for ver in self.PG_DOUBLE_PERCENT_VERSIONS]):
            template = re.sub(r'%%', '%', template)
        return template

    PG_DOUBLE_PERCENT_VERSIONS = ['2.4.4', '2.4.2', '2.4.1', '2.4.0', '2.5.1x']

    def _pg_install_trigger_function(self, table_name, pk_column_name, history_table_name, history_values, history_table_column_names):
        history_values = mark_safe(history_values) # don't want html entities in place of e.g. "
        history_table_column_names = mark_safe(history_table_column_names) # don't want html entities in place of e.g. "
        sql_statement = self._render(_pg_trigger_function_template, locals())
        logger.debug('executing sql: %s', sql_statement)
        self._execute_as_is(sql_statement)
        return

        sql_statement = self._render(self._pg_quote_by_version(_pg_trigger_function_template), locals())
        logger.debug('executing sql: %s', sql_statement)
        cursor = connection.cursor()
        sql_statement = AsIs(sql_statement) #didnt help with encoding
        f = open('/tmp/mog', 'w')
        f.write(cursor.mogrify('%s', [sql_statement]))
        f.close()
        cursor.execute('%s', [sql_statement])

    def _pg_create_trigger_on_table(self, table_name):
        trigger_args = ''
        sql_statement = self._render(_pg_trigger_template, locals())
        self._execute_as_is(sql_statement)
        return


        trigger_args = ''
        sql_statement = self._render(self._pg_quote_by_version(_pg_trigger_template), locals())
        logger.debug('executing sql: %s', sql_statement)
        cursor = connection.cursor()
        cursor.execute(sql_statement)

    def write_to_db_log(self, message):
        '''
        Helper utility for writing to database log.
        This is good for debugging database-related problems, when it is useful to see the
        executed SQL interleaved with python logging messages.
        '''
        # ensure it fits in one line and nothing harmful is written
        if self.db_logging_enabled:
            #message = re.sub(r'[^0-9a-zA-Z_ :.\-,()#\[\]+@$<>;*!=/]', '?', message.strip())
            message = re.sub(r'[^0-9a-zA-Z_ :.\-,()#\[\]+@$<>;*!=/{}]', '?', message.strip())
            cursor = connection.cursor()
            cursor.execute('SELECT trans_history_logger(%s)', ('trans_history: ' + str(message),))

    def _pg_install_log_util(self):
        '''
        Install helper utility procedure for logging to postgres log from django application.
        '''
        _logger_proc_plpgsql = '''
            CREATE OR REPLACE FUNCTION trans_history_logger(msg varchar) RETURNS void AS $PROC$
                BEGIN
                    -- quote with
                    raise NOTICE '%', msg;
                END;
            $PROC$ LANGUAGE plpgsql STRICT IMMUTABLE;
        '''
        self._execute_as_is(_logger_proc_plpgsql)
        return
        cursor = connection.cursor()
        sql_statement = self._pg_quote_by_version(_logger_proc_plpgsql)
        sql_statement = AsIs(sql_statement)
        cursor.execute('%s', [sql_statement]) #, ('%',)

    def _execute_as_is(self, sql_statement):
        cursor = connection.cursor()
        #sql_statement = self._pg_quote_by_version(sql_statement)
        sql_statement = AsIs(sql_statement) # prevent quoting of ' etc. in pl/pgsql code
        cursor.execute('%s', [sql_statement])

    def _render(self, template, context_dict):
        t = Template(template)
        return t.render(Context(context_dict)).strip()


    #def _add_or_replace_proc(self, model):
    #    '''
    #    Install procedures to the main table that react to create/update/delete operations by updating the history table.
    #    '''
    #    schema = ''
    #    table_name = 'personnel_organization'
    #
    #    sql = '''CREATE TRIGGER log_history AFTER INSERT OR UPDATE OR DELETE ON ' %(schema)s '.' %(table_name)s ' FOR EACH ROW EXECUTE PROCEDURE organization_history_insert();'''
    #    sql = sql % locals()

history_backend = PostgresHistoryBackend()
