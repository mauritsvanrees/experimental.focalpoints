from plone.app.tiles.imagescaling import AnnotationStorage
from plone.app.tiles.imagescaling import ImageScale
from plone.app.tiles.imagescaling import ImageScaling
from plone.protect.interfaces import IDisableCSRFProtection
from plone.rfc822.interfaces import IPrimaryFieldInfo
from zope.interface import alsoProvides


class TileImageScaling(ImageScaling):
    def scale(self, fieldname=None, scale=None, height=None, width=None, **parameters):
        if fieldname is None:
            primary = IPrimaryFieldInfo(self.context, None)
            if primary is None:
                return
            fieldname = primary.fieldname
        if scale is not None:
            available = self.available_sizes
            if scale not in available:
                return None
            width, height = available[scale]
        storage = AnnotationStorage(self.context, self.modified)
        # CHANGED: We do not pass a factory here, which is long deprecated anyway,
        # but rely on storage.scale to find the right IImageScaleFactory adapter.
        # info = storage.scale(
        #     factory=self.create, fieldname=fieldname, height=height, width=width, **parameters
        # )
        info = storage.scale(
            fieldname=fieldname, height=height, width=width, **parameters
        )
        if info is not None:
            # CHANGED: moved the csrf disabling here.
            # Disable Plone 5 implicit CSRF to allow scaling on GET
            alsoProvides(self.request, IDisableCSRFProtection)
            info["fieldname"] = fieldname
            scale_view = ImageScale(self.context, self.request, **info)
            return scale_view
