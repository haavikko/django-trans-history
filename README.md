## Library for tracking changes in Postgres database.

This project is work in progress. Not recommended for general use.

## Design goals

*  Maintain full history of database state
*  Query the database as it was at any given time:
   old_rev = Revision.objects.get_by_timestamp(datetime(nnnnn))
   User.history(revision=old_rev).filter(organizations_name='foo')
   changed_users = old_rev.get_changed_objects(clss=User).filter(name='bar'): # return all objects that were changed at this revision
   changes = old_rev.get_all_changed_objects(): # return all objects that were changed at this revision
   with (history.at_rev(rev=Revision.objects.get_by_timestamp(datetime(nnnnn))):
      User.history.filter(...)
      Organization.history.filter(...)
*  Query the database across revisions
   Revision.objects.filter(committed_by=1234) # audit trail of actions performed by a certain user 
*  Queries to the latest database version suffer no performance penalty.
*  Changes to an existing database schema should not be required, and external (non-django) tools should not need to
   filter out the history data.
*  Database writes will be a bit slower, but updating the history should be a O(n log(n)) operation at most (?? related objects and the number of objects changed within a transactio)
*  Revisions created in the database should match database transaction boundaries.
*  History should be maintained even when the database is accessed from outside of the Django application.
   This necessitates a non-Django component in the mix and makes the system database-dependant.
*  Restoring old versions and deleted objects
   User.history(revision=old_rev).filter(name__ilike='bar').restore() # restore all fields. If object was deleted, undelete it.
   User.history(revision=old_rev).filter(name__ilike='bar').restore(fields=['name', 'organizations']) # just some users and some fields
   Revision.objects.get_by_timestamp(datetime(nnnnn)).restore_all() # restore all data in the database to a previous state
   Revision.objects.get_by_timestamp(datetime(nnnnn)).rollback_all_later_revisions() # works by deleting objects, INCLUDING history
*  Track history of 3rd-party models without changing their code (such as django.contrib.auth.User)  
*  Take history tracking into use in an existing system. (TODO: maybe a management command to create initial "create" revisions?
*  Compare changes between revisions (like ("diff"))
   for attribute, value, revision in User.history.diff(pk=1234, from_revision=old_rev, to_revision=other_revision):
     print('%s was changed to %s at %s by %s', attribute, value, revision.committed_at, revision.committed_by.name)
* Manual modification of history tables is possible

"nice to have" features
* "just works" level integration with existing projects
* Django admin interface integration
* Minimal need for custom code in application

support model inheritance (abstract/non-abstract)?

Unsupported features
* Database independence. Support for each database back-end must be implemented separately. Project is aimed at Postgres.

## Troubleshooting

It is normal to receive messages like 'trigger "trans_history_trigger_auth_user" for table "auth_user" does not exist, skipping'

Troubleshooting
---------------

* Error "django.db.utils.DatabaseError: must be owner of database" while running transhistory_syncdb

Insufficient privileges on database. A quick fix is "GRANT ALL TO DATABASE <dbname> TO <username>", but
adapt to requirements.

* Error "INSERT has more expressions than target columns" in postgresql log

Check that the columns in main table and log table (and corresponding Django models) match.

* ERROR:  too many parameters specified for RAISE

This error is related to psycopg2 quoting. psycopg2 uses % to identify argument placeholders in sql.
The procedures that are installed also use %% 
This problem has been detected with psycopg2 2.0.13 and may apply to later versions too
Resolution: Add TRANSHISTORY_DOUBLE_PERCENT=True to your settings.py file.

* The <MyModelName>History tables are empty after installation

This is by design. If you would like populate the history table with current values,
do something like:
>>> MyModel.objects.all().update(id=F('id'))
Which forces the history triggers to run for all table rows.
This may take a long time if table is large!

* Error while inserting data to history table - wrong data type

Ensure that the columns in database table and django model definition are in the same order (needs fixing).

* IndexError: tuple index out of range while running transhistory_syncdb

* Error in postgresql or django log files, while inserting data to history table
For example: CONTEXT:  SQL statement "INSERT INTO dm_mytablehistory VALUES(DEFAULT,  $1 ,  $2 ,  $3 ,  $4 ,  $5 ,  $6 ,  $7 ,  $8 ,  $9 ,  $10 )"

Has the DB structure changed? re-run transhistory_syncdb.

* transhistory_syncdb management command seems to take forever

Some other (maybe idle) connection is probably holding a lock on one of the tables.
In order to create procedures, the code needs to acquire locks on all tables. Close all database clients (such as Django shell).
Check pg_locks.


