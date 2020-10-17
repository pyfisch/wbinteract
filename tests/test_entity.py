import unittest

from .context import wbinteract


class TestItem(unittest.TestCase):
    def test_fetch_universe_item(self):
        site = wbinteract.Wikibase("www.wikidata.org")
        universe = site.item("Q1")
        # label
        self.assertEqual(universe.labels["la"], "universum")
        label_languages = list(universe.labels)
        self.assertGreater(len(label_languages), 150)
        self.assertListEqual(list(universe.labels.keys()), label_languages)
        label_values = list(universe.labels.values())
        self.assertEqual(len(label_languages), len(label_values))
        label_items = list(universe.labels.items())
        self.assertEqual(len(label_languages), len(label_items))
        self.assertEqual(universe.labels["fr"], universe.labels.get("fr"))
        # description
        self.assertEqual(
            universe.descriptions["la"], "res quae omnem materiam et spatium continet",
        )
        # alias
        self.assertIn("Weltall", universe.aliases["de"])
        # TODO: enable again
        # sitelink
        # self.assertFalse("frwikivoyage" in universe.sitelinks)
        # enwiki_sitelink = universe.sitelinks["enwiki"]
        # self.assertEqual(enwiki_sitelink.title, "Universe")
        # good_article_badge = site.item("Q17437798")
        # self.assertEqual(enwiki_sitelink.badges, [good_article_badge])
        # Claims with Qualifiers
        # Hypothesis: the universe is a universe (class of parallel universes)
        claim = next(iter(universe.claims.p("P31")))
        self.assertEqual(claim.p, wbinteract.EntityId(site, "P31"))
        universe_class = wbinteract.EntityId(site, "Q36906466")
        self.assertEqual(claim.value, universe_class)
        self.assertEqual(len(claim.qualifiers), 1)
        qualifier = next(iter(claim.qualifiers.p("P5102")))
        hypothesis = wbinteract.EntityId(site, "Q41719")
        self.assertEqual(qualifier.value, hypothesis)

    def test_fetch_non_existant_item(self):
        site = wbinteract.Wikibase("www.wikidata.org")
        with self.assertRaises(wbinteract.EntityMissingError):
            item = site.item("Q96680735")

    def test_douglas_adams_claims(self):
        site = wbinteract.Wikibase("www.wikidata.org")
        item = site.item("Q42")
        item.fetch()
        # GND id
        gnd_id = next(iter(item.claims.p("P227")))
        self.assertEqual(gnd_id.mainsnak.p, wbinteract.EntityId(site, "P227"))
        self.assertEqual(gnd_id.mainsnak.value, "119033364")
        self.assertEqual(gnd_id.rank, wbinteract.Rank.NORMAL)
        # FIXME: enable again
        # self.assertGreaterEqual(len(gnd_id.references), 2)
        # Property:P1 does not exist
        statements_p1 = item.claims.p("P1")
        self.assertEqual(len(statements_p1), 0)


class TestProperty(unittest.TestCase):
    def test_property(self):
        wikidata = wbinteract.Wikibase("www.wikidata.org")
        date_of_birth = wikidata.property("P569")
        self.assertEqual(date_of_birth.datatype, "time")
