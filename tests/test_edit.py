import random
import unittest
from decimal import Decimal

from .context import wbinteract
from wbinteract import *

TEST_ITEM = "Q204828"

wd = wbinteract.Wikibase.from_config("test.wikidata.org")


class TestEditEntity(unittest.TestCase):
    def test_set_remove_french_label(self):
        item = Item(wd, TEST_ITEM)
        label = str(random.randint(0, 100_000))
        # Add label
        item.labels["fr"] = label
        item.save("set french label")
        self.assertEqual(item.labels["fr"], label)
        # Remove label
        del item.labels["fr"]
        item.save()
        self.assertNotIn("fr", item.labels)

    def test_set_descriptions(self):
        item = Item(wd, TEST_ITEM)
        description = str(random.randint(0, 100_000))
        item.descriptions["de"] = description
        item.descriptions["fr"] = description
        item.save("German + French descriptions")

    def test_set_remove_french_description_and_alias(self):
        item = Item(wd, TEST_ITEM)
        description = str(random.randint(0, 100_000))
        alias = str(random.randint(0, 100_000))
        # Add French description and an alias
        item.descriptions["fr"] = description
        item.aliases["fr"].add(alias)
        item.save()
        self.assertEqual(item.descriptions["fr"], description)
        self.assertIn(alias, item.aliases["fr"])
        # Remove all French aliases
        item.aliases["fr"].clear()
        item.save()
        self.assertEqual(len(item.aliases["fr"]), 0)

    def test_add_remove_claim(self):
        item = Item(wd, TEST_ITEM)
        value = "foobar" + str(random.randint(0, 100_000))
        item.claims.add(Statement(wd, PropertyValueSnak(wd.id("P95180"), value)))
        item.save(f"add claim P95180 = {value}")
        # add a qualifier
        claim = next(iter(item.claims.p("P95180")))
        claim.qualifiers.add(wd.snak("P664", "some qualifier"))
        item.save("add a qualifier to P95180")
        item = Item(wd, TEST_ITEM)
        claim = [claim for claim in item.claims.p("P95180") if claim.value == value][0]
        item.claims.remove(claim)
        item.save(f"remove claim P95180 = {value}")

    def test_add_claims_with_rank(self):
        item = Item(wd, TEST_ITEM)
        item.claims.add(
            Statement(
                wd, PropertyValueSnak(wd.id("P95180"), "preferred"), Rank.PREFERRED
            )
        )
        item.claims.add(
            Statement(wd, PropertyValueSnak(wd.id("P95180"), "normal"), Rank.NORMAL)
        )
        item.claims.add(
            Statement(
                wd, PropertyValueSnak(wd.id("P95180"), "deprecated"), Rank.DEPRECATED,
            )
        )
        item.save()

    def test_add_entity_claim(self):
        item = Item(wd, TEST_ITEM)
        item.claims.add(wd.claim("P796", wd.id("P31")))
        item.save()

    def test_add_monolingual_claim(self):
        item = Item(wd, TEST_ITEM)
        item.claims.add(wd.claim("P246", MonolingualText("Brezel", "de")))
        item.save()

    def test_add_globe_coordinate_claim(self):
        item = Item(wd, TEST_ITEM)
        coordinate = GlobeCoordinate(45.9763, 7.6588, precision=0.0001)
        item.claims.add(wd.claim("P35", coordinate))
        item.save()

    def test_add_quantity_claim(self):
        item = Item(wd, TEST_ITEM)
        quantity = Quantity(42)
        item.claims.add(wd.claim("P69", quantity))
        item.save()

    def test_add_time_claim(self):
        item = Item(wd, TEST_ITEM)
        item.claims.add(wd.claim("P83", Time("2018-05-04", Time.DAY)))
        item.save()

    def test_add_claim_with_qualifier(self):
        item = wd.item(TEST_ITEM)
        eggs = wd.snak("P664", "eggs")
        item.claims.add(wd.claim("P664", "spam", qualifiers=[eggs]))
        item.save()

    @unittest.skip
    def test_remove_add_sitelink(self):
        item = Item(wd, TEST_ITEM)
        # Remove ALL sitelinks
        item.sitelinks.clear()
        # Add one enwiki sitelink (without any badges)
        item.sitelinks["enwiki"] = "Foobar2000"
        item.save()
        self.assertEqual(len(item.sitelinks), 1)
        self.assertEqual(item.sitelinks["en"].title, "Foobar2000")
