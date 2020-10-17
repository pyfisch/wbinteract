import enum
import collections

from wbinteract.snak import *
from wbinteract.snak_set import SnakSet
from wbinteract.util import ChangeMixin


class Rank(enum.Enum):
    """Ranks provide a simple selection/filtering criterion
    for statements.
    
    .. py:data:: PREFERRED
    .. py:data:: NORMAL
    .. py:data:: DEPRECATED
    """

    PREFERRED = "preferred"
    NORMAL = "normal"
    DEPRECATED = "deprecated"


class Statement(ChangeMixin):
    def __init__(
        self,
        site,
        mainsnak,
        rank=Rank.NORMAL,
        qualifiers=None,
        references=None,
        id=None,
    ):
        self._site = site
        self._id = id
        self._mainsnak = mainsnak
        self._rank = rank
        # Store qualifiers
        if qualifiers is None:
            self._qualifiers = Qualifiers(site)
        else:
            self._qualifiers = Qualifiers.from_iterable(site, qualifiers)
        self._qualifiers._attach(self._notify)
        # Store references
        if references is None:
            self._references = References(site)
        else:
            self._references = References.from_iterable(site, qualifiers)
        self._references._attach(self._notify)

    @property
    def mainsnak(self):
        """The main snak of the statement."""
        return self._mainsnak

    @property
    def p(self):
        """Property of the main snak."""
        return self._mainsnak.p

    @property
    def value(self):
        """Value of the main snak."""
        if isinstance(self._mainsnak, PropertyValueSnak):
            return self._mainsnak.value
        else:
            return None

    @property
    def rank(self):
        """Rank of the entire statement."""
        return self._rank

    @rank.setter
    def rank(self, value):
        self._rank = value
        self._notify()

    @property
    def qualifiers(self):
        return self._qualifiers

    @property
    def references(self):
        return self._references

    @staticmethod
    def from_json(site, json):
        assert json["type"] == "statement"
        mainsnak = PropertySnak.from_json(site, json["mainsnak"])
        rank = Rank(json["rank"])
        statement = Statement(site, mainsnak, rank, id=json["id"])
        statement.qualifiers._update_from_json(json.get("qualifiers", dict()))
        statement.references._update_from_json(json.get("references", []))
        return statement

    def to_json(self):
        json = {
            "type": "statement",
            "mainsnak": self._mainsnak.to_json(),
            "rank": self.rank.value,
            "qualifiers": self.qualifiers.to_json(),
            "references": self.references.to_json(),
        }
        if self._id is not None:
            json["id"] = self._id
        return json


class Qualifiers(SnakSet):
    def _update_from_json(self, data):
        SnakSet._update_from_json(
            self, data, lambda json: PropertySnak.from_json(self._site, json)
        )


class References(ChangeMixin, collections.abc.MutableSequence):
    def __init__(self, site):
        self._site = site
        self._store = []

    @staticmethod
    def from_iterable(site, iterable):
        references = References(site)
        for record in iter(iterable):
            record._attach(self._notify)
            references._store.append(record)
        return references

    def _update_from_json(self, json_list):
        for json_record in json_list:
            # TODO: store snaks order
            record = ReferenceRecord(self._site, json_record["hash"])
            record._attach(self._notify)
            record._update_from_json(
                json_record["snaks"],
                lambda json: PropertySnak.from_json(self._site, json),
            )
            self._store.append(record)

    def to_json(self):
        return [record.to_json() for record in self._store]

    def __getitem__(self, key):
        return self._store[key]

    def __setitem__(self, key, value):
        value._attach(self._notify)
        self._store[key] = value
        self._notify()

    def __delitem__(self, key):
        del self._store[key]
        self._notify()

    def __len__(self):
        return len(self._store)

    def insert(self, index, value):
        value._attach(self._notify)
        self._store.insert(index, value)
        self._notify()


class ReferenceRecord(SnakSet):
    def __init__(self, site, hash=None):
        super().__init__(site)
        self._hash = hash

    def to_json(self):
        snaks = SnakSet.to_json(self)
        json = {"snaks": snaks}
        if self._hash is not None:
            json["hash"] = self._hash
        return json
