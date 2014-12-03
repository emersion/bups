class OptionsDict(object):
    def __init__(self, d):
        self.__dict__ = d
    def __getattr__(self, name):
        return None