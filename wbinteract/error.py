class APIError(Exception):
    def __init__(self, errors):
        self.errors = errors

    def __str__(self):
        return " / ".join(
            (error["code"] + ": " + error["text"]) or error["code"]
            for error in self.errors
        )


class EntityMissingError(Exception):
    def __init__(self, entity):
        self.entity = entity


class NoCurrentEditError(Exception):
    def __init__(self):
        pass
