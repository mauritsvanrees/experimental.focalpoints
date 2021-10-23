from zope.interface import Interface


class IImageTransformer(Interface):
    pass


class IWantImageTransforming(Interface):
    """Marker interface for types that want transforming based on focalpoints."""
