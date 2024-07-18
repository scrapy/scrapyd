import warnings


class ScrapydDeprecationWarning(Warning):
    """Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+
    """


class WarningMeta(type):
    def __init__(cls, name, bases, clsdict):
        wrapper_classes = tuple(c.__bases__ for c in bases if isinstance(c, WarningMeta))
        classes = tuple(c for (c,) in wrapper_classes)
        if classes:
            warnings.warn(
                f"{cls!r} inherits from {classes!r} which {['is', 'are'][min(2, len(classes)) - 1]} "
                "deprecated and will be removed from a later scrapyd release",
                ScrapydDeprecationWarning,
                stacklevel=2,
            )
        super().__init__(name, bases, clsdict)


def deprecate_class(cls):
    class WarningMeta2(WarningMeta):
        pass

    for b in cls.__bases__:
        if type(b) not in WarningMeta2.__bases__:
            WarningMeta2.__bases__ += (type(b),)

    def new_init(*args, **kwargs):
        warnings.warn(f"{cls!r} will be removed from a later scrapyd release", ScrapydDeprecationWarning, stacklevel=2)
        return cls.__init__(*args, **kwargs)

    return WarningMeta2(cls.__name__, (cls,), {"__init__": new_init})
