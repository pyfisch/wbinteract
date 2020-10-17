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
