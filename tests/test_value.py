from decimal import Decimal
import unittest

from .context import wbinteract

from wbinteract.value import *


MONOLINGUAL_TEXT_JSON = {
    "value": {"text": "maison", "language": "fr"},
    "type": "monolingualtext",
}
GLOBE_COORDINATE_JSON = {
    "value": {
        "latitude": 45.9763,
        "longitude": 7.6588,
        "altitude": None,
        "precision": 0.0001,
        "globe": "http://www.wikidata.org/entity/Q2",
    },
    "type": "globecoordinate",
}
QUANTITY_JSON = {"value": {"amount": "+9000", "unit": "1"}, "type": "quantity"}
TIME_JSON = {
    "value": {
        "time": "+2017-03-03T00:00:00Z",
        "timezone": 0,
        "before": 0,
        "after": 0,
        "precision": 11,
        "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
    },
    "type": "time",
}


class DummySite(wbinteract.Wikibase):
    def __init__(self):
        super().__init__("wikibase.example.org")


dummy_site = DummySite()


class TestMonolingualText(unittest.TestCase):
    def test_from_json(self):
        house = MonolingualText.from_json(dummy_site, MONOLINGUAL_TEXT_JSON)
        self.assertEqual(house.text, "maison")
        self.assertEqual(house.language, "fr")

    def test_eq(self):
        foobar = MonolingualText("foobar", "en")
        foobar_fr = MonolingualText("foobar", "fr")
        self.assertEqual(foobar, foobar)
        self.assertNotEqual(foobar, foobar_fr)
        self.assertNotEqual(foobar, "foobar")


class TestGlobeCoordinate(unittest.TestCase):
    def test_from_json(self):
        matterhorn = GlobeCoordinate.from_json(dummy_site, GLOBE_COORDINATE_JSON)
        self.assertEqual(matterhorn.longitude, 7.6588)
        self.assertEqual(matterhorn.precision, GlobeCoordinate.DEGREE / 10_000)


class TestQuantity(unittest.TestCase):
    def test_from_json(self):
        value = Quantity.from_json(dummy_site, QUANTITY_JSON)
        self.assertEqual(value.amount, Decimal(9000))
        self.assertEqual(value.unit, "1")


class TestTime(unittest.TestCase):
    def test_from_json(self):
        time = Time.from_json(dummy_site, TIME_JSON)
        self.assertEqual(time.time, "+2017-03-03")
        self.assertEqual(time.calendar_model, Time.GREGORIAN)
