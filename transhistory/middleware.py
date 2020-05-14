'''
Created on 29 Nov 2012

@author: mhaa
'''
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
from builtins import object
from .models import Revision
class CurrentUserMiddleware(object):
    def process_request(self, request):
        if request.POST and request.user.is_authenticated():
            Revision.objects.set_current_committer(request.user.id)
