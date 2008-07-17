"""Pylons application test package

When the test runner finds and executes tests within this directory,
this file will be loaded to setup the test environment.

It registers the root directory of the project in sys.path and
pkg_resources, in case the project hasn't been installed with
setuptools. It also initializes the application via websetup (paster
setup-app) with the project's test.ini configuration file.
"""
import os
import sys
from unittest import TestCase

import pkg_resources
import paste.fixture
import paste.script.appinstall
from paste.deploy import loadapp
from paste.deploy import appconfig
from addressbook.config.environment import load_environment
from routes import url_for

__all__ = ['url_for', 'TestController']

here_dir = os.path.dirname(os.path.abspath(__file__))
conf_dir = os.path.dirname(os.path.dirname(here_dir))

sys.path.insert(0, conf_dir)
pkg_resources.working_set.add_entry(conf_dir)
pkg_resources.require('Paste')
pkg_resources.require('PasteScript')

test_file = os.path.join(conf_dir, 'test.ini')
## don't run setup-app
# cmd = paste.script.appinstall.SetupCommand('setup-app')
# cmd.run([test_file])
conf = appconfig('config:' + test_file)
load_environment(conf.global_conf, conf.local_conf)

from addressbook import model
from addressbook.model import meta
from fixture import SQLAlchemyFixture
from fixture.style import NamedDataStyle

dbfixture = SQLAlchemyFixture(
    env=model,
    engine=meta.engine,
    style=NamedDataStyle()
)

def setup():
    meta.metadata.create_all(meta.engine)

def teardown():
    meta.metadata.drop_all(meta.engine)

class TestController(TestCase):

    def __init__(self, *args, **kwargs):
        wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        self.app = paste.fixture.TestApp(wsgiapp)
        TestCase.__init__(self, *args, **kwargs)
    
    def setUp(self):
        meta.Session.remove() # clear any stragglers from last test
    
    def tearDown(self):
        pass