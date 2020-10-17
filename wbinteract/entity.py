import collections
import contextlib
import json
import enum
import re

from wbinteract.error import EntityMissingError, NoCurrentEditError
from wbinteract.snak import *
from wbinteract.value import EntityId, _value_from_json

from wbinteract.snak_set import SnakSet
from wbinteract.statement import Statement
from wbinteract.util import ChangeMixin


class Entity(ChangeMixin):
    def __init__(self, site, id=None):
        self._id = id
        self._site = site
        self._exists = None
        self._data = None
        self._parts = dict()
        self._current_edit = None
        self._unsaved_changes = dict()

    def __eq__(self, other):
        return (
            isinstance(other, Entity)
            and self.site == other.site
            and self.id == other.id
        )

    @classmethod
    def from_json(cls, site, json_entity):
        id = json_entity["id"]
        if "missing" in json_entity:
            raise ValueError(f"Entity {id} is missing!")
        entity = cls(site)
        entity._update_from_json(json_entity)
        entity._id = json_entity["id"]
        return entity

    @property
    def id(self):
        return self._id

    @property
    def site(self):
        return self._site

    def fetch(self):
        r = self.site.api(action="wbgetentities", ids=self.id)
        data = r["entities"][self.id]
        if "missing" in data:
            raise EntityMissingError(self)
        self._update_from_json(data)

    def _update_from_json(self, data):
        self._data = data
        for (key, part) in self._parts.items():
            part._update_from_json(data[key])

    def _notify(self, *changed_aspect):
        change_tracker = self._unsaved_changes
        for segment in changed_aspect:
            change_tracker = change_tracker.setdefault(segment, dict())

    def save(self, summary=None):
        changes = dict()
        for (key, unsaved) in self._unsaved_changes.items():
            changes_part = self._parts[key]._changes_to_json(unsaved)
            if changes_part is not None:
                changes[key] = changes_part
        site = self.site
        r = site.api(
            "wbeditentity",
            id=self.id,
            data=json.dumps(changes),
            summary=summary,
            token=site.tokens["csrftoken"],
            bot=site.bot,
        )
        self._update_from_json(r["entity"])


class Item(Entity):
    def __init__(self, site, id=None):
        assert id is None or re.fullmatch("Q\d+", id)
        super().__init__(site, id)
        self._parts["labels"] = Labels(self)._attach(self._notify, "labels")
        self._parts["descriptions"] = Descriptions(self)._attach(
            self._notify, "descriptions"
        )
        self._parts["aliases"] = Aliases(self)._attach(self._notify, "aliases")
        self._parts["claims"] = Claims(self)._attach(self._notify, "claims")
        if self.id is not None:
            self.fetch()

    @property
    def labels(self):
        return self._parts["labels"]

    @property
    def descriptions(self):
        return self._parts["descriptions"]

    @property
    def aliases(self):
        return self._parts["aliases"]

    @property
    def claims(self):
        if self._data is None:
            self.fetch()
        return self._parts["claims"]


class Property(Entity):
    def __init__(self, site, id=None):
        assert id is None or re.fullmatch("P\d+", id)
        super().__init__(site, id)
        self._parts["labels"] = Labels(self)._attach(self._notify, "labels")
        self._parts["descriptions"] = Descriptions(self)._attach(
            self._notify, "descriptions"
        )
        self._parts["aliases"] = Aliases(self)._attach(self._notify, "aliases")
        self._parts["claims"] = Claims(self)._attach(self._notify, "claims")
        if self.id is not None:
            self.fetch()

    @property
    def datatype(self):
        return self._data["datatype"]

    @property
    def labels(self):
        return self._parts["labels"]

    @property
    def descriptions(self):
        return self._parts["descriptions"]

    @property
    def aliases(self):
        return self._parts["aliases"]

    @property
    def claims(self):
        return self._parts["claims"]


class InfiniteDict(collections.defaultdict):
    def __init__(self):
        collections.defaultdict.__init__(self, self.__class__)


class Edit:
    def __init__(self, entity):
        self._entity = entity
        self._changes = InfiniteDict()
        self.summary = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if type is not None:
            # Undo all changes
            if self._entity._data is not None:
                self._entity._update_from_json(self._entity._data)
            return
        changes = dict()
        for (key, part) in self._entity._parts.items():
            changes_part = part._changes_to_json(self._changes[key])
            if changes_part is not None:
                changes[key] = changes_part
        site = self._entity.site
        r = site.api(
            "wbeditentity",
            id=self._entity.id,
            data=json.dumps(changes),
            summary=self.summary,
            token=site.tokens["csrftoken"],
            bot=site.bot,
        )
        self._entity._update_from_json(r["entity"])


class ChangeContext:
    def __init__(self, entity, changed_path):
        self._entity = entity
        self._changed_path = changed_path

    def __enter__(self):
        if self._entity._current_edit is None:
            raise NoCurrentEditError

    def __exit__(self, type, value, traceback):
        if type is not None:
            return
        changed = self._entity._current_edit._changes
        for segment in self._changed_path[:-1]:
            changed = changed[segment]
        changed[self._changed_path[-1]] = True


class Labels(ChangeMixin, collections.abc.MutableMapping):
    def __init__(self, entity):
        self._entity = entity
        self.__store = dict()

    def _update_from_json(self, data):
        self.__store = {key: value["value"] for (key, value) in data.items()}

    def _changes_to_json(self, changed_languages):
        changes = [
            {"language": lang, "value": self.__store[lang],}
            for lang in changed_languages
            if lang in self.__store
        ]
        changes.extend(
            {"language": lang, "remove": ""}
            for lang in changed_languages
            if lang not in self.__store
        )
        return changes

    def __getitem__(self, key):
        return self.__store[key]

    def __setitem__(self, key, value):
        self.__store[key] = value
        self._notify(key)

    def __delitem__(self, key):
        del self.__store[key]
        self._notify(key)

    def __iter__(self):
        return iter(self.__store)

    def __len__(self):
        return len(self.__store)


class Descriptions(ChangeMixin, collections.abc.MutableMapping):
    def __init__(self, entity):
        self._entity = entity
        self.__store = dict()

    def _update_from_json(self, data):
        self.__store = {key: value["value"] for (key, value) in data.items()}

    def _changes_to_json(self, changed_languages):
        changes = [
            {"language": lang, "value": self.__store[lang],}
            for lang in changed_languages
            if lang in self.__store
        ]
        changes.extend(
            {"language": lang, "remove": ""}
            for lang in changed_languages
            if lang not in self.__store
        )
        return changes

    def __setitem__(self, key, value):
        self.__store[key] = value
        self._notify(key)

    def __delitem__(self, key):
        del self.__store[key]
        self._notify(key)

    def __getitem__(self, key):
        return self.__store[key]

    def __iter__(self):
        return iter(self.__store)

    def __len__(self):
        return len(self.__store)


class Aliases(ChangeMixin, collections.abc.Mapping):
    def __init__(self, entity):
        self._entity = entity
        self.__store = dict()

    def _update_from_json(self, data):
        self.__store = {
            key: AliasSet._from_json(key, value)._attach(self._notify, key)
            for (key, value) in data.items()
        }

    def _changes_to_json(self, changed):
        changes = []
        for (lang, aliases) in changed.items():
            for alias in aliases:
                if alias in self[lang]:
                    changes.append({"language": lang, "value": alias})
                else:
                    changes.append({"language": lang, "value": alias, "remove": ""})
        return changes

    def __getitem__(self, key):
        if key not in self.__store:
            self.__store[key] = AliasSet(key)._attach(self._notify, key)
        return self.__store[key]

    def __iter__(self):
        return iter(self.__store)

    def __len__(self):
        return len(self.__store)


class AliasSet(ChangeMixin, collections.abc.MutableSet):
    def __init__(self, language):
        self._language = language
        self.__store = set()

    @staticmethod
    def _from_json(language, data):
        alias_set = AliasSet(language)
        alias_set.__store = set(elem["value"] for elem in data)
        return alias_set

    def __contains__(self, item):
        return item in self.__store

    def __iter__(self):
        return iter(self.__store)

    def __len__(self):
        return len(self.__store)

    def add(self, value):
        self.__store.add(value)
        self._notify(value)

    def discard(self, value):
        self.__store.discard(value)
        self._notify(value)


class Claims(SnakSet):
    def __init__(self, entity):
        super().__init__(entity._site)
        self._entity = entity
        self.__store = None

    def _update_from_json(self, data):
        SnakSet._update_from_json(
            self,
            data,
            lambda json: Statement.from_json(self._entity._site, json)._attach(
                self._notify, json["id"]
            ),
        )

    def _changes_to_json(self, changed):
        changed_claims = [key for key in changed.keys() if key != "new"]
        changes = []
        for claim in iter(self):
            if claim._id is None:
                changes.append(claim.to_json())
            elif claim._id in changed_claims:
                changed_claims.remove(claim._id)
                changes.append(claim.to_json())
        for id in changed_claims:
            changes.append({"id": id, "remove": ""})
        return changes

    def remove(self, elem):
        self._store[elem.p].remove(elem)
        if elem._id is not None:
            self._notify(elem._id)
