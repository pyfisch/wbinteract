from wbinteract.value import EntityId, _value_from_json


class PropertySnak:
    """Base class for all property snaks.

    Do not use directly.
    """

    def __init__(self, p):
        assert isinstance(p, EntityId)
        assert p.id.startswith("P")
        self._property = p

    @property
    def p(self):
        return self._property

    @staticmethod
    def from_json(site, json):
        if json["snaktype"] == "value":
            return PropertyValueSnak.from_json(site, json)
        elif json["snaktype"] == "novalue":
            return PropertyNoValueSnak.from_json(site, json)
        elif json["snaktype"] == "somevalue":
            return PropertySomeValueSnak.from_json(site, json)
        else:
            raise ValueError()

    def to_json(self):
        raise NotImplementedError


class PropertyValueSnak(PropertySnak):
    """A ``PropertyValueSnak`` describes that an Entity has a certain property
    with a given value.
    """

    def __init__(self, p, value):
        super().__init__(p)
        self._value = value

    def __repr__(self):
        return f"PropertyValueSnak({repr(self.p)}, {repr(self.value)})"

    def __eq__(self, other):
        return (
            isinstance(other, PropertyValueSnak)
            and self.p == other.p
            and self.value == other.value
        )

    @property
    def value(self):
        return self._value

    @staticmethod
    def from_json(site, json):
        assert json["snaktype"] == "value"
        return PropertyValueSnak(
            EntityId(site, json["property"]), _value_from_json(site, json["datavalue"]),
        )

    def to_json(self):
        if isinstance(self.value, str):
            value = {"type": "string", "value": self._value}
        else:
            value = self.value.to_json()
        return {
            "snaktype": "value",
            "property": self.p.id,
            "datavalue": value,
        }


class PropertyNoValueSnak(PropertySnak):
    """A ``PropertyNoValueSnak`` describes that an entity has no values
    for a certain property.
    """

    def __init__(self, property):
        super().__init__(property)

    def __repr__(self):
        return f"PropertyNoValueSnak({repr(self.p)})"

    def __eq__(self, other):
        return isinstance(other, PropertyNoValueSnak) and self.p == other.p

    @staticmethod
    def from_json(site, json):
        assert json["snaktype"] == "novalue"
        return PropertyNoValueSnak(EntityId(site, json["property"]))

    def to_json(self):
        return {
            "snaktype": "novalue",
            "property": self.p.id,
        }


class PropertySomeValueSnak(PropertySnak):
    """A ``PropertySomeValueSnak`` describes that an entity has some value for
    a certain property, without saying anything about this value.
    """

    def __init__(self, property):
        super().__init__(property)

    def __repr__(self):
        return f"PropertySomeValueSnak({repr(self.p)})"

    def __eq__(self, other):
        return isinstance(other, PropertySomeValueSnak) and self.p == other.p

    @staticmethod
    def from_json(site, json):
        assert json["snaktype"] == "somevalue"
        return PropertySomeValueSnak(EntityId(site, json["property"]))

    def to_json(self):
        return {
            "snaktype": "somevalue",
            "property": self.p.id,
        }
