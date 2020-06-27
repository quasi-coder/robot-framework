import json


class Dotable(object):
    """
    Helper class to access the JSON-like configurations in .dot style notation.

    """

    @classmethod
    def parse(cls, v):
        if isinstance(v, _DotableDict):
            return v
        elif isinstance(v, dict):
            return _DotableDict(v)
        elif isinstance(v, list):
            return _DotableList(cls.parse(i) for i in v)
        elif isinstance(v, tuple):
            return _DotableTuple(cls.parse(i) for i in v)
        else:
            return v


class DotableCollection(object):
    '''
    Interface to expose.
    '''
    pass


class _DotableDict(dict, Dotable):
    __getattr__ = dict.__getitem__

    def __init__(self, d):
        self.update(**dict((k, Dotable.parse(v))
                           for k, v in d.iteritems()))  # in py3 use .items

    def __setitem__(self, key, value):
        super(_DotableDict, self).__setitem__(key, Dotable.parse(value))

    def __add__(self, other):
        if isinstance(other, dict):
            cpy = Dotable.parse(self.copy())
            cpy.update(other)
            return cpy
        else:
            raise TypeError("Expected _DotableDict, but was %s", type(other))

    def __radd__(self, left):
        if isinstance(left, dict):
            cpy = Dotable.parse(left.copy())
            cpy.update(self)
            return cpy
        else:
            raise TypeError("Expected _DotableDict, but was %s", type(left))

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=None, separators=(',', ': '))


class _DotableList(list, DotableCollection):
    def __init__(self, seq=()):
        super(_DotableList, self).__init__(Dotable.parse(seq))

    def append(self, p_object):
        super(_DotableList, self).append(Dotable.parse(p_object))

    def extend(self, iterable):
        super(_DotableList, self).extend(Dotable.parse(iterable))

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=None, separators=(',', ': '))


class _DotableTuple(tuple, DotableCollection):
    def __init__(self, seq=()):
        super(_DotableTuple, self).__init__(Dotable.parse(seq))

    def __add__(self, p_object):
        super(_DotableTuple, self).__add__(Dotable.parse(p_object))

    def __str__(self):
        return json.dumps(self, sort_keys=True, indent=None, separators=(',', ': '))
