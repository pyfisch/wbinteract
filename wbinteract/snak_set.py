import collections
import itertools
import logging

from wbinteract.value import EntityId
from wbinteract.util import ChangeMixin

import contextlib


class SnakSet(ChangeMixin, collections.abc.MutableSet):
    def __init__(self, site):
        self._site = site
        self._store = collections.defaultdict(list)

    @staticmethod
    def from_iterable(site, iterable):
        snak_set = SnakSet(site)
        for snak in iter(iterable):
            snak_set._store[snak.p].append(snak)
        return snak_set

    def to_json(self):
        return [snak.to_json() for snak in iter(self)]

    def _update_from_json(self, json_snak_dict, factory):
        self._store = collections.defaultdict(list)
        for snak in itertools.chain.from_iterable(json_snak_dict.values()):
            elem = factory(snak)
            self._store[elem.p].append(elem)

    def __contains__(self, elem):
        return elem in self._store[elem.p]

    def __iter__(self):
        return (snak for group in self._store.values() for snak in group)

    def __len__(self):
        return sum((len(group) for group in self._store.values()))

    def add(self, elem):
        if not elem in self:
            self._store[elem.p].append(elem)
            self._notify()

    def remove(self, elem):
        self._store[elem.p].remove(elem)
        self._notify()

    def discard(self, elem):
        try:
            self.remove(elem)
        except ValueError:
            pass

    def p(self, id):
        id = EntityId._from_str_or_id(self._site, id)
        return SnaksView(self, id)


class SnaksView(collections.abc.ValuesView):
    def __init__(self, snaks, id):
        self._snaks = snaks
        self._id = id

    def __contains__(self, elem):
        return elem in self._snaks[elem.p]

    def __iter__(self):
        return iter(self._snaks._store[self._id])

    def __len__(self):
        return len(self._snaks._store[self._id])
