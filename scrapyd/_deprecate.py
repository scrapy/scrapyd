import warnings
import inspect


class ScrapydDeprecationWarning(Warning):
    """Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+
    """
    pass


class WarningMeta(type):
    def __init__(cls, name, bases, clsdict):
        offending_wrapper_classes = tuple(c.__bases__ for c in bases
                                          if isinstance(c, WarningMeta))
        offending_classes = tuple(c for c, in offending_wrapper_classes)
        if offending_classes:
            warnings.warn(
                '%r inherits from %r which %s deprecated'
                ' and will be removed from a later scrapyd release'
                % (cls, offending_classes,
                   ['is', 'are'][min(2, len(offending_classes))-1]),
                ScrapydDeprecationWarning,
            )
        super(WarningMeta, cls).__init__(name, bases, clsdict)


def deprecate_class(cls):
    class WarningMeta2(WarningMeta):
        pass
    for b in cls.__bases__:
        if type(b) not in WarningMeta2.__bases__:
            WarningMeta2.__bases__ += (type(b),)
    def new_init(*args, **kwargs):
        warnings.warn('%r will be removed from a later scrapyd release' % cls,
                      ScrapydDeprecationWarning)
        return cls.__init__(*args, **kwargs)
    return WarningMeta2(cls.__name__, (cls,), {'__init__': new_init})
