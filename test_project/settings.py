# -*- coding: utf-8 -*-

# Settings for running the test application testcases

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
import os
import sys

DEBUG = True
TEMPLATE_DEBUG = DEBUG
PROJECT_ROOT = os.path.normpath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, '..'))

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'personnel',                      # Or path to database file if using sqlite3.
        'USER': 'personnel',                      # Not used with sqlite3.
        'PASSWORD': 'personnel',                  # Not used with sqlite3.
        'PORT': '5432',
        'HOST': 'localhost',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Helsinki'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = PROJECT_ROOT + '/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'MNKopiqeu0r9hIACS()TQ#öphwssadkjbfuasdjco+e33q2ja7(YHOLA'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'personnel.urls'

'''
TEMPLATE_DIRS = (
    PROJECT_ROOT + "/personnel/templates/"
)
'''

TEMPLATES = [
{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'DIRS': [
             os.path.join(PROJECT_ROOT, '/personnel/templates/'),
    ],
    'OPTIONS': {
        # 'debug': DEBUG,
        'context_processors':
            (
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.i18n',
            'django.template.context_processors.media',
            # not needed? 'django.template.context_processors.static',
            # not needed? 'django.template.context_processors.tz',
            # not needed? 'django.template.context_processors.csrf',
            'django.contrib.messages.context_processors.messages',
            'ws.dws.context_processors.django_conf_settings',
            )
    }
},
]


INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'personnel',
    'transhistory',
    'cli_query', # for querying objects from command line
    'django_nose', # testing nose test runner
)

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

LOGIN_URL = "/login"

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'postgres':{
            'level':'DEBUG',
            'class':'transhistory.db_log_util.PostgresLogHandler',
            'formatter': 'simple'
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'personnel': {
            'handlers': ['console', 'postgres'], # change in real use
            'level': 'DEBUG',
            'propagate': True,
        },
        'transhistory': {
            'handlers': ['console', 'postgres'], # change in real use
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

