from plone.protect.interfaces import IDisableCSRFProtection
from plone.scale.storage import AnnotationStorage
from Products.Five import BrowserView
from zope.interface import alsoProvides
from .focalpoint.subscriber import determine_focalpoints

import logging
import PIL.Image


logger = logging.getLogger(__name__)


def friendly_size(image_field):
    with image_field.open() as image_file:
        try:
            pil_image = PIL.Image.open(image_file)
        except OSError:
            # Probably: cannot identify image file
            # Locally I have experimental.gracefulblobmissing,
            # so image blobs may be wrong.
            width = height = 0
        else:
            width, height = pil_image.size
    if width == height:
        aspect = "square"
    elif width > height:
        aspect = "landscape"
    else:
        aspect = "portrait"
    return f"width {width} x height {height} ({aspect})"


class ClearScales(BrowserView):
    """Remove all scale annotations from this context.

    This is meant to ease debugging, so you don't need to worry whether old
    scales still linger, even after changing the image, and especially when
    editing and switching back and forth between two images.

    Actually, let's only clear all scales with '?force=1' in the request.
    Why? There may be html that points to a scale that you now remove.
    This html can be in a cache.
    And in listings, for example section search, you may use portal/@@image_scale
    to get scales from a brain, and this is also cached.
    So this is mostly useful for debugging locally.

    When not forcing, we call the (private) _cleanup method, which is more subtle,
    keeping scales that are less than a day old.

    But first we mark the context as modified.  That helps clean up more.
    Also, when the type supports it, this means we redo the focal point detection
    """

    def __call__(self):
        determine_focalpoints(self.context)
        storage = AnnotationStorage(self.context)
        count = len(storage)
        try:
            force = int(self.request["force"]) > 0
        except (KeyError, ValueError, TypeError):
            force = False
        if force:
            storage.clear()
        else:
            # Since this is a private method, let's try/except.
            try:
                storage._cleanup()
            except AttributeError:
                logger.warning(
                    "Got AttributeError calling private storage._cleanup method."
                )
        new_count = len(storage)
        alsoProvides(self.request, IDisableCSRFProtection)
        try:
            focal_point = self.context.image.focal_point
        except AttributeError:
            focal_point = None
        return (
            f"Cleared {count - new_count} scales from annotation storage.\n"
            f"{new_count} scales left.\n"
            f"Image dimensions: {friendly_size(self.context.image)}\n"
            f"Focal point: {focal_point}."
        )


class ScalesTest(BrowserView):
    def size(self):
        return friendly_size(self.context.image)
