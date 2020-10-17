from dataclasses import dataclass
from decimal import Decimal
import re


@dataclass(frozen=True)
class EntityId:
    """Link to another entity.
    
    This is distinct from actual the actual
    item/property/... to ensure that it can't be mutated.
    """

    # FIXME: Wikibase
    site: object
    id: str

    @staticmethod
    def _from_str_or_id(site, id):
        if isinstance(id, EntityId):
            assert site is id.site, "the site and id.site values don't match"
            return id
        elif isinstance(id, str):
            return EntityId(site, id)
        else:
            raise TypeError("id must be either a str or EntityId")

    def get(self):
        """Get the referenced entity."""
        raise NotImplementedError()

    @staticmethod
    def from_json(site, json):
        assert json["type"] == "wikibase-entityid"
        return EntityId(site, json["value"]["id"])

    def to_json(self):
        return {"type": "wikibase-entityid", "value": {"id": self.id}}


@dataclass(frozen=True)
class MonolingualText:
    """Value containing text in a specific language.
    The language used is indicated by a language code.

    The word "house" in French:

    >>> text = MonolingualText("maison", "fr")
    """

    text: str
    language: str

    @staticmethod
    def from_json(site, json):
        assert json["type"] == "monolingualtext"
        value = json["value"]
        return MonolingualText(value["text"], value["language"])

    def to_json(self):
        return {
            "type": "monolingualtext",
            "value": {"text": self.text, "language": self.language},
        }


@dataclass(frozen=True)
class GlobeCoordinate:
    """Value for geographical coordinates.

    The ``globe`` parameter indicates the celestial body the coordinate
    relates to. It is given as an URI for the relevant entity.

    The precision of coordinates is expressed as fractions of a degree.
    For convenience these constants are provided that can be used to
    describe precision, e.g. *to 1/10 of an arcsecond*
    is ``1 / 10 * ARCSECOND``.

    .. py:data:: DEGREE
    
        One *degree* is 1/360 of a full circle.
        Common coordinate precisions are ±10° up to ±0.000001°.

    .. py:data:: ARCMINUTE

        An *arcminute* is 1/60 of a degree.

    .. Py:data:: ARCSECOND

        An *arcsecond* is 1/60 of an arcminute.

    >>> matterhorn = GlobeCoordinate(45.9763, 7.6588, precision=0.0001)
    >>> matterhorn.latitude
    45.9763
    """

    latitude: float
    longitude: float
    precision: float = None
    globe: str = None

    DEGREE = 1
    ARCMINUTE = 1 / 60
    ARCSECOND = 1 / 60 / 60

    @staticmethod
    def from_json(site, json):
        assert json["type"] == "globecoordinate"
        value = json["value"]
        return GlobeCoordinate(
            value["latitude"], value["longitude"], value["precision"], value["globe"],
        )

    def to_json(self):
        return {
            "type": "globecoordinate",
            "value": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "precision": self.precision,
                "globe": self.globe,
            },
        }


@dataclass(frozen=True)
class Quantity:
    """Physical (or other) quantities with an optional unit.

    The ``unit`` is stated as an URI for the relevant entity.
    If the quantity has no unit the field is ``None``.

    Optionally an upper bound and a lower bound can be specified.
    While arbitrary values can be entered many users ignore this
    data, the current (August 2020) Wikidata UI only
    shows symmetric bounds.

    To ensure no precision is lost due to floating-point rounding
    errors use :py:class:`decimal.Decimal`.
    """

    amount: Decimal
    unit: str = "1"
    upper_bound: Decimal = None
    lower_bound: Decimal = None

    @staticmethod
    def from_json(site, json):
        assert json["type"] == "quantity"
        value = json["value"]
        upper_bound = value.get("uppperBound")
        lower_bound = value.get("lowerBound")
        return Quantity(
            Decimal(value["amount"]),
            value["unit"],
            Decimal(upper_bound) if upper_bound else None,
            Decimal(lower_bound) if lower_bound else None,
        )

    def to_json(self):
        return {
            "type": "quantity",
            "value": {
                "amount": str(self.amount),
                "unit": self.unit,
                "lowerBound": self.lower_bound,
                "upperBound": self.upper_bound,
            },
        }


@dataclass(frozen=True)
class Time:
    """Value for time (or rather dates).

    Right now only dates, but no instants with hours and minutes,
    can be stored in Wikibase.

    >>> Time("1990-10-03", precision=Time.DAY)
    Time(time='+1990-10-03', precision=11, calendar_model='http://www.wikidata.org/entity/Q1985727')

    The precision of a data is stated with a number between
    0 (billion years) and 14 (second), some common precisions
    are provided as an associated constant:

    .. py:data:: CENTURY
    .. py:data:: DECADE
    .. py:data:: YEAR
    .. py:data:: MONTH
    .. py:data:: DAY

    Two calendar models are supported:

    .. py:data:: GREGORIAN

        Date is in the `Gregorian calendar`_,
        which is the calendar commonly used today.
        Dates before the introduction of this calendar
        are assumed to be in the Proleptic Gregorian calendar.

    .. py:data:: JULIAN

        Date is in the `Julian calendar`_.

    .. _Gregorian calendar: https://en.wikipedia.org/wiki/Gregorian_calendar
    .. _Julian calendar: https://en.wikipedia.org/wiki/Julian_calendar
    """

    GREGORIAN = "http://www.wikidata.org/entity/Q1985727"
    JULIAN = "http://www.wikidata.org/entity/Q1985786"

    CENTURY = 7
    DECADE = 8
    YEAR = 9
    MONTH = 10
    DAY = 11

    time: str
    precision: int
    calendar_model: str = GREGORIAN

    def __init__(self, time, precision, calendar_model=GREGORIAN):
        assert re.match("[-+]?\d+-\d+-\d+", time)
        if time[0] not in "+-":
            time = "+" + time
        object.__setattr__(self, "time", time)
        object.__setattr__(self, "precision", precision)
        object.__setattr__(self, "calendar_model", calendar_model)

    @staticmethod
    def from_json(site, json):
        assert json["type"] == "time"
        value = json["value"]
        # Note: Discards unused hours, minutes and seconds.
        time = re.match("([-+]\d+-\d+-\d+)T\d{2}:\d{2}:\d{2}Z", value["time"])[1]
        return Time(time, value["precision"], value["calendarmodel"])

    def to_json(self):
        time = self.time + "T00:00:00Z"
        return {
            "type": "time",
            "value": {
                "time": time,
                "precision": self.precision,
                "calendarmodel": self.calendar_model,
                "timezone": 0,
                "before": 0,
                "after": 0,
            },
        }


def _value_from_json(site, json):
    """Take a parsed JSON fragment and construct
    the corresponding value.
    """
    return {
        "string": lambda site, json: json["value"],
        "wikibase-entityid": EntityId.from_json,
        "monolingualtext": MonolingualText.from_json,
        "globecoordinate": GlobeCoordinate.from_json,
        "quantity": Quantity.from_json,
        "time": Time.from_json,
    }[json["type"]](site, json)
