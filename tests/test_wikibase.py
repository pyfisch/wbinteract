import unittest

from .context import wbinteract


class TestWikibase(unittest.TestCase):
    def test_purge(self):
        site = wbinteract.Wikibase("test.wikidata.org")
        r = site.api(action="purge", titles="Q42")
        self.assertTrue(r["batchcomplete"])
        self.assertEqual(r["purge"], [{"ns": 0, "title": "Q42", "purged": True}])

    def test_unknown_action(self):
        site = wbinteract.Wikibase("test.wikidata.org")
        with self.assertRaises(wbinteract.APIError):
            r = site.api(action="unknown-action")
