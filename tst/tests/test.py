import unittest
import os

import tst
from tst.jsonfile import JsonFile

import contextlib

@contextlib.contextmanager
def monkey_patch(module, fn_name, patch):
    unpatch = getattr(module, fn_name)
    setattr(module, fn_name)
    try:
        yield
    finally:
        setattr(module, fn_name, unpatch)


class TestMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def test_get_config(self):
        # monkey patch CONFIDIR
        ACTUAL_CONFIGDIR = tst.tst.CONFIGDIR
        FAKE_CONFIGDIR = '/tmp/tst_tests'
        tst.tst.CONFIGDIR = FAKE_CONFIGDIR

        # monkey patch CONFIGILE
        ACTUAL_CONFIGFILE = tst.tst.CONFIGFILE
        FAKE_CONFIGFILE = tst.tst.CONFIGDIR + '/fake_config.yaml'
        if os.path.exists(FAKE_CONFIGFILE):
            os.remove(FAKE_CONFIGFILE)
        tst.tst.CONFIGFILE = FAKE_CONFIGFILE

        # perform mock test
        config = tst.get_config()
        assert isinstance(config, JsonFile)
        assert config.data == {
            "sites": [{
                "name": "demo",
                "url": "https://raw.githubusercontent.com/daltonserey/tst-demo/master"
            }]
        }
        
        # reset CONFIGDIR and CONFIGFILE
        tst.tst.CONFIGDIR = ACTUAL_CONFIGDIR
        tst.tst.CONFIGFILE = ACTUAL_CONFIGFILE


    def test_2(self):
        assert tst.coverit() == 1


if __name__ == '__main__':
    unittest.main()
