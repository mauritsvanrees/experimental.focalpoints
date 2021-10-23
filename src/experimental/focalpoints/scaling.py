"""Create scales using thumbor.

Scaling starts with the @@images view.
This is defined in class plone.namedfile.scaling.ImageScaling.
It has a 'scale' method.
This calls AnnotationStorage(self.context).scale(...)

This calls:

    scaling_factory = IImageScaleFactory(self.context, None)
    result = scaling_factory(**parameters)

This normally finds the plone.namedfile.scaling.DefaultImageScalingFactory class,
but we have overridden this to the class below.

The class calls self.create_scale, which calls scaleImage from plone.scale,
and this calls:

    image = scalePILImage(image, width, height, mode, direction=direction)

Note that we started at plone.namedfile, then plone.scale,
then namedfile again, then scale again.
If we redo this, it can't possibly get any more confusing...

One of these three methods/functions is probably the best place for calling thumbor:
create_scale, scaleImage, scalePILImage

The result is unpacked:

    data, format_, dimensions = result
    width, height = dimensions

A word on direction and mode: direction is actually the old name
See plone.scale.scale: get_scale_mode and scalePILImage.
These are different names for the same scaling mode/direction,
where the first is the canonical one:

- contain, scale-crop-to-fit, down
- cover, scale-crop-to-fill, up
- scale, keep, thumbnail

When should we do something different?
Probably not for all modes.
We want to use thumbor for its focalpoint detection.
This only matters when cropping, so: contain and cover.
We want to start with improving syncrecipe images,
and the recipe_view.pt used direction=down, so mode=contain.

"""
from .focalpoint.transformer import CropFocalPointsTransformer
from Acquisition import aq_base
from io import BytesIO
from plone.namedfile.file import FILECHUNK_CLASSES
from plone.namedfile.scaling import DefaultImageScalingFactory
from plone.rfc822.interfaces import IPrimaryFieldInfo
from plone.scale.interfaces import IImageScaleFactory
from plone.scale.scale import get_scale_mode
from Products.CMFPlone.utils import safe_encode
from ZODB.blob import BlobFile
from ZODB.POSException import ConflictError
from zope.interface import implementer

import logging
import PIL.Image
import six


try:
    from plone.tiles.interfaces import IPersistentTile
except ImportError:
    IPersistentTile = None

logger = logging.getLogger(__name__)
# For debugging, this might help, to throw away scales sooner:
# from plone.scale import storage
# # Do not keep scales around for a day.
# storage.KEEP_SCALE_MILLIS = 0


@implementer(IImageScaleFactory)
class ExperimentalImageScalingFactory(DefaultImageScalingFactory):
    def __init__(self, context):
        self.context = context
        if IPersistentTile is not None and IPersistentTile.providedBy(context):
            self.is_tile = True
            # We get data from the tile:
            self.data_context = context.data
            # This is the actual content item (Page, News Item, etc):
            self.content_context = context.context
        else:
            self.is_tile = False
            self.data_context = context
            self.content_context = context

    def get_original_value(self):
        if self.is_tile:
            return self.data_context.get(self.fieldname)
        return getattr(self.content_context, self.fieldname, None)

    def url(self):
        base = self.content_context.absolute_url()
        if not self.is_tile:
            return base
        return "{}/@@{}/{}".format(base, self.context.__name__, self.context.id)

    def __call__(
        self,
        fieldname=None,
        direction="thumbnail",
        height=None,
        width=None,
        scale=None,
        **parameters,
    ):
        """Factory for image scales."""
        # CHANGED: Store the fieldname, so we can use it in create_scale.
        if fieldname is None:
            primary = IPrimaryFieldInfo(self.context, None)
            if primary is None:
                return
            fieldname = primary.fieldname
        self.fieldname = fieldname
        # This change was enough at first, and we could call:
        # return super().__call__(
        #     fieldname=fieldname,
        #     direction=direction,
        #     height=height,
        #     width=width,
        #     scale=scale,
        #     **parameters,
        # )
        # But now we need to take over all the code, to support tiles.

        # CHANGED: Call new method get_original_value.
        # orig_value = getattr(self.context, fieldname, None)
        orig_value = self.get_original_value()
        if orig_value is None:
            return

        if height is None and width is None:
            dummy, format_ = orig_value.contentType.split("/", 1)
            return None, format_, (orig_value._width, orig_value._height)
        elif (
            not parameters
            and height
            and width
            and height == getattr(orig_value, "_height", None)
            and width == getattr(orig_value, "_width", None)
        ):
            dummy, format_ = orig_value.contentType.split("/", 1)
            return orig_value, format_, (orig_value._width, orig_value._height)
        orig_data = None
        try:
            orig_data = orig_value.open()
        except AttributeError:
            orig_data = getattr(aq_base(orig_value), "data", orig_value)
        if not orig_data:
            return
        # Handle cases where large image data is stored in FileChunks instead
        # of plain string
        if isinstance(orig_data, tuple(FILECHUNK_CLASSES)):
            # Convert data to 8-bit string
            # (FileChunk does not provide read() access)
            orig_data = str(orig_data)

        # If quality wasn't in the parameters, try the site's default scaling
        # quality if it exists.
        if "quality" not in parameters:
            quality = self.get_quality()
            if quality:
                parameters["quality"] = quality

        if not getattr(orig_value, "contentType", "") == "image/svg+xml":
            try:
                result = self.create_scale(
                    orig_data,
                    direction=direction,
                    height=height,
                    width=width,
                    **parameters,
                )
            except (ConflictError, KeyboardInterrupt):
                raise
            except Exception:
                logger.exception(
                    'Could not scale field {0!r} with value "{1!r}" of {2!r}'.format(
                        self.fieldname,
                        orig_value,
                        self.url(),
                    ),
                )
                return
            if result is None:
                return
        else:
            if isinstance(orig_data, (six.text_type)):
                orig_data = safe_encode(orig_data)
            if isinstance(orig_data, (bytes)):
                orig_data = BytesIO(orig_data)

            result = orig_data.read(), "svg+xml", (width, height)

        data, format_, dimensions = result
        mimetype = "image/{0}".format(format_.lower())
        # Note: we could create a patch so that every time we create a NamedBlobFile
        # or set data in it, we determine focal points.  But this code would also
        # be called here, where we create a scale, even though we have just used
        # the previously determined focal points to create that scale!
        # So determining it here, would be useless.  We could change the init
        # of the NamedBlobFile class to have original=True, and pass
        # original=False here.  Only determine focal points when original is True.
        # Or do something funky like: set request.DONT_DO_IT, create the NamedBlobFile,
        # remove request.DONT_DO_IT, and let the code check this attribute.
        # Either way, seems a bit iffy.
        value = orig_value.__class__(
            data,
            contentType=mimetype,
            filename=orig_value.filename,
        )
        value.fieldname = fieldname

        # make sure the file is closed to avoid error:
        # ZODB-5.5.1-py3.7.egg/ZODB/blob.py:339: ResourceWarning:
        # unclosed file <_io.FileIO ... mode='rb' closefd=True>
        if isinstance(orig_data, BlobFile):
            orig_data.close()

        return value, format_, dimensions

    def create_scale(self, data, direction, height, width, **parameters):
        """Scale the given image data to another size and return the result
        as a string or optionally write in to the file-like `result` object.

        Here is the original docstring, so we know what we need to support.

        The `image` parameter can either be the raw image data (ie a `str`
        instance) or an open file.

        The `quality` parameter can be used to set the quality of the
        resulting image scales.

        The return value is a tuple with the new image, the image format and
        a size-tuple.  Optionally a file-like object can be given as the
        `result` parameter, in which the generated image scale will be stored.

        The `width`, `height`, `mode` parameters will be passed to
        :meth:`scalePILImage`, which performs the actual scaling.

        The generated image is a JPEG image, unless the original is a PNG or GIF
        image. This is needed to make sure alpha channel information is
        not lost, which JPEG does not support.
        """
        # Pass the default mode (contain) and the direction to get the canonical mode name.
        mode = get_scale_mode("contain", direction)
        logger.debug(
            f"create_scale({self.content_context.portal_type} at {self.url()}, mode={mode}, height={height}, width={width}, {parameters})"
        )
        if mode != "contain":
            # We don't want cropping, just a boring scale. Plone can handle this itself.
            # Note: mode 'cover' says it scales up (when needed) and then crops,
            # but in my testing the cropping is never needed.  So standard Plone
            # can handle this.  See comment in CropFocalPointsTransformer in
            # method '_unused_handle_cover' (formerly: 'handle_cover').
            return super().create_scale(data, direction, height, width, **parameters)

        field = self.get_original_value()

        # Future: use getAdapters to get named adapters and call them all.
        transformer = CropFocalPointsTransformer(self.context)
        transformer.prepare(field, mode)
        if not transformer.available:
            # No focal points were set.
            return super().create_scale(data, direction, height, width, **parameters)

        # Open the image with PIL.
        if isinstance(data, bytes):
            data = BytesIO(data)
        try:
            pil_image = PIL.Image.open(data)
        except OSError:
            # Probably: cannot identify image file
            # Locally I have experimental.gracefulblobmissing,
            # so image blobs may be wrong.
            logger.warning("OSError opening image file at %s", self.url())
            # Try upstream for good measure.
            return super().create_scale(data, direction, height, width, **parameters)

        # Note that the original create_scale calls scaleImage,
        # which does various things, to improve the end result.
        # I take over some of it.

        # When we create a new image during scaling we loose the format
        # information, so remember it here.  We will use it when saving.
        # Scale format will be JPEG or PNG.
        format_ = pil_image.format
        if format_ not in ("PNG", "GIF"):
            # Always generate JPEG, except if format is PNG or GIF.
            format_ = "JPEG"
        elif format_ == "GIF":
            # GIF scaled looks better if we have 8-bit alpha and no palette
            format_ = "PNG"
        icc_profile = pil_image.info.get("icc_profile")

        # Note: some transformers may change the image in place,
        # others could return a new one.
        new_image = transformer.run(pil_image, target_width=width, target_height=height)
        if new_image:
            pil_image = new_image

        # We need to handle two parameters that are used when saving the image to disk:
        # quality and result.
        quality = parameters.get("quality", 88)
        result = parameters.get("result", None)

        new_result = False
        if result is None:
            result = BytesIO()
            new_result = True
        # Save the PIL image to the result, using the format determined above.
        pil_image.save(
            result,
            format_,
            quality=quality,
            optimize=True,
            progressive=True,
            icc_profile=icc_profile,
        )
        if new_result:
            result = result.getvalue()
        else:
            result.seek(0)

        return result, format_, pil_image.size
