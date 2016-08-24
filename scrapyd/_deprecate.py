import warnings
import inspect


class ScrapydDeprecationWarning(Warning):
    """Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+
    """
    pass


class WarningMeta(type):
    def __init__(cls, name, bases, clsdict):
        offending_classes = tuple(c for c in bases if isinstance(c, WarningMeta))
        if offending_classes:
            warnings.warn(
                '%r inherits from %r which %s deprecated'
                ' and will be removed from a later scrapyd version'
                % (cls, offending_classes,
                   ['is', 'are'][min(2, len(offending_classes))-1]),
                ScrapydDeprecationWarning,
            )
        super(WarningMeta, cls).__init__(name, bases, clsdict)


def deprecate_class(cls):
    base_metaclasses = set(type(b) for b in cls.__bases__) | {WarningMeta}
    class WarningMeta2(WarningMeta):
        pass
    for b in base_metaclasses:
        if b not in WarningMeta2.__bases__:
            WarningMeta2.__bases__ += (b,)
    #WarningMeta2 = type('WarningMeta', tuple(base_metaclasses), {})

    class cls2(cls):
        __metaclass__ = WarningMeta2
    return cls2
