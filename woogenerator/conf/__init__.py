# -*- coding: utf-8 -*-
"""
Module for configuration of woogenerator
"""
import sys
import os

MODULE_PATH = os.path.dirname(__file__)
MODULE_LOCATION = os.path.dirname(MODULE_PATH)
sys.path.insert(0, MODULE_LOCATION)

# Core configuration
CONF_DIR = os.path.join(MODULE_LOCATION, 'conf')
assert os.path.exists(CONF_DIR), "conf dir: %s should exist" % CONF_DIR
DEFAULTS_COMMON_PATH = os.path.join(CONF_DIR, 'defaults_common.yaml')
DEFAULTS_PROD_PATH = os.path.join(CONF_DIR, 'defaults_prod.yaml')
DEFAULTS_USER_PATH = os.path.join(CONF_DIR, 'defaults_user.yaml')

# User controlled configuration
DEFAULT_TESTMODE = True
DEFAULT_LOCAL_WORK_DIR = os.path.expanduser('~/Documents/woogenerator')
DEFAULT_LOCAL_PROD_PATH = 'conf_prod.yaml'
DEFAULT_LOCAL_PROD_TEST_PATH = 'conf_prod_test.yaml'
DEFAULT_LOCAL_USER_PATH = 'conf_user.yaml'
DEFAULT_LOCAL_USER_TEST_PATH = 'conf_user_test.yaml'
DEFAULT_LOCAL_IN_DIR = 'input/'
DEFAULT_LOCAL_OUT_DIR = 'output/'
DEFAULT_LOCAL_LOG_DIR = 'logs/'
DEFAULT_LOCAL_IMG_RAW_DIR = 'imgs_raw/'
DEFAULT_LOCAL_IMG_CMP_DIR = 'imgs_cmp/'
DEFAULT_MASTER_NAME = 'master'
DEFAULT_SLAVE_NAME = 'slave'