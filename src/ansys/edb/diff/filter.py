class FilterBase:
    def __init__(self, logger=None):
        self.logger = logger

    def execute(self, entry: tuple) -> bool:
        if not isinstance(entry, tuple) or len(entry) != 3:
            return False
        val1, val2, is_equal = entry
        return is_equal
