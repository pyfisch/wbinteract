import doctest
import unittest
import os

from .context import wbinteract


def load_tests(loader, tests, ignore):
    this_dir = os.path.dirname(__file__)
    tests.addTests(loader.discover(this_dir))
    tests.addTests(doctest.DocTestSuite(wbinteract.value))
    tests.addTests(doctest.DocTestSuite(wbinteract.wikibase))
    return tests
