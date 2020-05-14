#!/usr/bin/env python
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
import os
import sys

if __name__ == "__main__":
    # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ws.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    if '--debug-on-exception' in sys.argv:
        try:
            # tests read sys.argv directly
            sys.argv = [v for v in sys.argv if v != '--debug-on-exception']
            execute_from_command_line(sys.argv)
        except:
            import traceback, pdb
            traceback.print_exc()
            print('')
            pdb.post_mortem()
    else:
        execute_from_command_line(sys.argv)
