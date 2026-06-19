from _Project.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable Cloudinary for tests
CLOUDINARY_CLOUD_NAME = ''
CLOUDINARY_API_KEY = ''
CLOUDINARY_API_SECRET = ''

# Disable external APIs
REVERSE_IMAGE_API_KEY = ''
SERPAPI_KEY = ''
OPENROUTER_API_KEY = ''
SEARXNG_BASE_URL = 'http://localhost:8888'