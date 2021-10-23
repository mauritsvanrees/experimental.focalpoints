from dataclasses import dataclass


@dataclass
class FocalPoint:
    """Class for focal points.

    Data classes are new in Python 3.7.
    See https://docs.python.org/3/library/dataclasses.html
    We could also use namedtuples, available from 3.1,
    but let's try the shiny new thing.

    At the moment this is only used during calculations,
    and never stored in the ZODB.  If this ever changes,
    we should test if this dataclass works well.

    Thumbor has thumbor.point.FocalPoint which has more data:
    x, y, weight, height, width, origin
    I don't think we need the extra for now.

    In 'origin' we could store the name of the adapter that
    found the focal point.  Or 'user' if a way is made for users
    to specify the focal point by hand.  Those should get a big weight then.
    """

    x: int
    y: int
    weight: float = 1.0
