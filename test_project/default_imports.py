from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Helpers for command-line use

from future import standard_library
standard_library.install_aliases()
from builtins import *
import os, sys
import codecs
from io import StringIO

from django import forms
from django.template import loader
from django.template import Context
from django.template import RequestContext
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.db import transaction
from django.core import serializers
import simplejson 
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Count,Avg
from django.utils.translation import ugettext as _
from django.core.mail import send_mail
from django.db import connection

from transhistory import *
from personnel import models

