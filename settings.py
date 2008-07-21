# Django settings for the example project.
import os
DEBUG = os.environ['SERVER_SOFTWARE'].startswith('Dev')
TEMPLATE_DEBUG = DEBUG
ROOT_URLCONF = 'urls'

import os
ROOT_PATH = os.path.dirname(__file__)
TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or
    # "C:/www/django/templates".  Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    ROOT_PATH + '/templates',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)


INSTALLED_APPS = (
    'imyp'
)
