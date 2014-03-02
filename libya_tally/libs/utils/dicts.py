from itertools import chain


def flatten(l):
    return list(chain.from_iterable(l))


def keys_if_value(d):
    return [k for k, v in d.iteritems() if v]
