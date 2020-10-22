import itertools

import SPARQLWrapper

import wbinteract


class NoValue:
    def __repr__(self):
        return "NoValue"


class SomeValue:
    def __repr__(self):
        return "SomeValue"


NoValue = NoValue()
SomeValue = SomeValue()


class ChangeMixin:
    def _notify(self, *args):
        if hasattr(self, "_listener"):
            self._listener(*self._listener_data, *args)

    def _attach(self, listener, *data):
        self._listener = listener
        self._listener_data = data if data is not None else []
        return self


class QueryService:
    def __init__(self, endpoint, site, entity_url):
        self.endpoint = endpoint
        self.site = site
        self.entity_url = entity_url

    def get_items(self, query, item_name="item"):
        def get_id(line):
            return line[item_name]["value"].replace(self.entity_url, "")

        sparql = SPARQLWrapper.SPARQLWrapper(self.endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(SPARQLWrapper.JSON)
        result = sparql.query().convert()["results"]["bindings"]
        item_ids = (get_id(line) for line in result)
        while True:
            batch = list(itertools.islice(item_ids, 50))
            if not batch:
                break
            r = self.site.api(action="wbgetentities", ids=batch)
            for raw_entity in r["entities"].values():
                try:
                    yield wbinteract.Item.from_json(self.site, raw_entity)
                except ValueError:
                    pass
