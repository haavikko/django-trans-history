## Library for tracking changes in Postgres database.

This project is work in progress. Not recommended for general use.

## Design goals

*  Maintain full history of database state
*  Query the database as it was at any given time:
   old_rev = Revision.objects.get_by_timestamp(datetime(nnnnn))
   # return all users that existed in the database at the specified time and belonged to organization named 'foo' at that time.
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
   # normally reverting to an old revision works by making a new one 
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

