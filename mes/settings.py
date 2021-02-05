"""
Django settings for mes project.

Generated by 'django-admin startproject' using Django 2.2.14.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
import datetime
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django.utils.translation import ugettext_lazy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '@(e8hu481p171x)jz!40a$@gt6@_=#2_g-sscjrc531tsxz0(d'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = eval(os.environ.get('DEBUG', 'True'))

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'drf_yasg',  # swagger文档插件    /api/v1/docs/swagger
    'django_filters',
    'production.apps.ProductionConfig',
    'plan.apps.PlanConfig',
    'basics.apps.BasicsConfig',
    'system.apps.SystemConfig',
    'recipe.apps.RecipeConfig',
    'docs.apps.DocsConfig',
    'quality.apps.QualityConfig',
    'inventory.apps.InventoryConfig',
    'spareparts.apps.SparepartsConfig',
    'terminal.apps.TerminalConfig',
    'equipment.apps.EquipmentConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'mes.middlewares.DisableCSRF',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'mes.middlewares.SyncMiddleware',
    'mes.middlewares.JwtTokenUserMiddleware',  # jwt-token嵌套django权限组件
]

ROOT_URLCONF = 'mes.urls'
AUTH_USER_MODEL = 'system.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'dist')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mes.wsgi.application'

# drf通用配置
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',  # 文档
    'DEFAULT_PERMISSION_CLASS': ('rest_framework.permissions.IsAuthenticated',),  # 权限
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),  # 认证
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),  # 过滤
    'DEFAULT_PAGINATION_CLASS': 'mes.paginations.DefaultPageNumberPagination',  # 分页
    'DATETIME_FORMAT': "%Y-%m-%d %H:%M:%S",
}

REST_FRAMEWORK_EXTENSIONS = {
    # 缓存时间(1小时)
    'DEFAULT_CACHE_RESPONSE_TIMEOUT': 60 * 10,
    # 缓存到哪里 (caches中配置的default)
    'DEFAULT_USE_CACHE': 'default',
}

JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=1),
    'JWT_ALLOW_REFRESH': True,
}

# LOGGING_DIR = os.environ.get('LOGGING_DIR', os.path.join(BASE_DIR, 'logs'))
#
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
#         },
#         'simple': {
#             'format': '%(levelname)s %(message)s'
#         },
#         'standard': {
#             'format': '%(asctime)s [%(threadName)s:%(thread)d] [%(name)s:%(lineno)d] '
#                       '[%(module)s:%(funcName)s] [%(levelname)s]- %(message)s'
#         },
#         'django_request': {
#             'format': '%(levelname)s %(asctime)s %(pathname)s %(module)s %(lineno)d %(message)s'
#                       ' status_code:%(status_code)d',
#             'datefmt': '%Y-%m-%d %H:%M:%S'
#         },
#         'django_db_backends': {
#             'format': '%(levelname)s %(asctime)s %(pathname)s %(module)s %(lineno)d %(message)s',
#             'datefmt': '%Y-%m-%d %H:%M:%S'
#         },
#     },
#     'filters': {
#         'require_debug_true': {
#             '()': 'django.utils.log.RequireDebugTrue',
#         },
#
#     },
#     'handlers': {
#         'console': {
#             'level': 'DEBUG',
#             'filters': ['require_debug_true'],
#             'class': 'logging.StreamHandler',
#             'formatter': 'standard'
#         },
#         'django_db_backends': {
#             'level': 'DEBUG',
#             'filters': ['require_debug_true'],
#             'class': 'logging.StreamHandler',
#             'formatter': 'django_db_backends'
#         },
#         'django_request': {
#             'level': 'DEBUG',
#             'filters': ['require_debug_true'],
#             'class': 'logging.StreamHandler',
#             'formatter': 'django_request'
#         },
#         'timedRotatingFile': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(LOGGING_DIR, 'api_log.log'),
#             'when': 'midnight',
#             'backupCount': 10,
#             'formatter': 'standard',
#             'interval': 1,
#         },
#         'errorFile': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(LOGGING_DIR, 'error.log'),
#             'when': 'midnight',
#             'backupCount': 10,
#             'formatter': 'standard',
#             'interval': 1,
#         },
#         'syncFile': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(LOGGING_DIR, 'sync.log'),
#             'when': 'midnight',
#             'backupCount': 10,
#             'formatter': 'standard',
#             'interval': 1,
#         },
#         'asyncFile': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(LOGGING_DIR, 'async.log'),
#             'when': 'midnight',
#             'backupCount': 10,
#             'formatter': 'standard',
#             'interval': 1,
#         },
#         'sendFile': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(LOGGING_DIR, 'send.log'),
#             'when': 'midnight',
#             'backupCount': 10,
#             'formatter': 'standard',
#             'interval': 1,
#         },
#         'qualityFile': {
#             'level': 'DEBUG',
#             'class': 'logging.handlers.TimedRotatingFileHandler',
#             'filename': os.path.join(LOGGING_DIR, 'quality.log'),
#             'when': 'midnight',
#             'backupCount': 10,
#             'formatter': 'standard',
#             'interval': 1,
#         },
#     },
#     'loggers': {
#         'django.db.backends': {
#             'handlers': ['django_db_backends'],
#             'propagate': True,
#             'level': 'DEBUG' if DEBUG else 'INFO',
#         },
#         'django.request': {
#             'handlers': ['django_request'],
#             'level': 'ERROR',
#             'propagate': False,
#         },
#         'api_log': {
#             'handlers': ['timedRotatingFile'],
#             'level': 'DEBUG' if DEBUG else 'INFO',
#         },
#         'error_log': {
#             'handlers': ['errorFile'],
#             'level': 'DEBUG' if DEBUG else 'INFO',
#         },
#         'sync_log': {
#             'handlers': ['syncFile'],
#             'level': 'DEBUG' if DEBUG else 'INFO',
#         },
#         'async_log': {
#             'handlers': ['asyncFile'],
#             'level': 'INFO',
#         },
#         'send_log': {
#             'handlers': ['sendFile'],
#             'level': 'INFO',
#         },
#         'quality_log': {
#             'handlers': ['qualityFile'],
#             'level': 'INFO',
#         },
#     },
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'my_cache_table',  # 设置一个数据库存放缓存的表名
    },
    'OPTIONS': {
        'MAX_ENTRIES': 30,  # 最大缓存个数（默认300）
        'CULL_FREQUENCY': 3,  # 缓存到达最大个数之后，剔除缓存个数的比例，即：1/CULL_FREQUENCY（默认3），3：表示1/3
    },
    # 这边只的是缓存的key：p1:1:func_name
    'KEY_PREFIX': 'p1',  # 缓存key的前缀（默认空）
    'VERSION': 1,  # 缓存key的版本（默认1）
    'KEY_FUNCTION': "func_name"  # 生成key的函数（默认函数会生成为：【前缀:版本:key】）
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False

AUTH_USER_MODEL = 'system.User'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR, "static/"))

STATICFILES_DIRS = [
    # os.path.join(BASE_DIR, 'static'),# 项目默认会有的路径，如果你部署的不仅是前端打包的静态文件，项目目录static文件下还有其他文件，最好不要删
    os.path.join(BASE_DIR, "dist/static"),  # 加上这条
]

MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, "media/"))
MEDIA_URL = '/media/'

LANGUAGES = (
    ('en-us', ugettext_lazy(u"English")),
    ('zh-hans', ugettext_lazy(u"简体中文")),
)

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

# LOGIN_URL = 'gui:login'
# LOGIN_REDIRECT_URL = 'gui:global-codes-manage'
# LOGOUT_REDIRECT_URL = 'gui:login'

# 跨域允许的请求方式，可以使用默认值，默认的请求方式为:
# from corsheaders.defaults import default_methods
CORS_ALLOW_METHODS = (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
)

# 允许跨域的请求头，可以使用默认值，默认的请求头为:
# from corsheaders.defaults import default_headers
# CORS_ALLOW_HEADERS = default_headers

CORS_ALLOW_HEADERS = (
    'XMLHttpRequest',
    'X_FILENAME',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'Pragma',
)

# 跨域请求时，是否运行携带cookie，默认为False
CORS_ALLOW_CREDENTIALS = True
# 允许所有主机执行跨站点请求，默认为False
# 如果没设置该参数，则必须设置白名单，运行部分白名单的主机才能执行跨站点请求
CORS_ORIGIN_ALLOW_ALL = True

# 上辅机部署地址
AUXILIARY_URL = os.environ.get('AUXILIARY_URL', 'http://127.0.0.1:9000/')
