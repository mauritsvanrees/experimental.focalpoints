"""
Parts copied from thumbor imaging service
https://github.com/thumbor/thumbor/wiki

Licensed under the MIT license:
http://www.opensource.org/licenses/mit-license
Copyright (c) 2011 globo.com thumbor@googlegroups.com
"""
from .detectors import FeatureFocalpointDetector

import logging
import math
import PIL.Image


# from .interfaces import IImageTransformer
# from .interfaces import IWantImageTransforming
# from zope.component import adapter
# from zope.interface import implementer
logger = logging.getLogger(__name__)


class BaseImageTransformer:
    # Future: Transforms are ordered, lowest number is run first.
    # order = 5000
    # By default this transform is available,
    # but 'prepare' can set it to False.
    available = True

    def __init__(self, context):
        # Note: context is usually a content item,
        # but could be a tile, or maybe a portlet.
        # So be careful when you make assumptions.
        self.context = context

    def prepare(self, field, mode, **kwargs):
        # Reset self.available, in case we reuse the transformer
        # for multiple fields.
        self.available = True
        self.field = field
        self.mode = mode
        if not hasattr(self, f"handle_{mode}"):
            self.available = False
            return

    def run(self, pil_image, **kwargs):
        handler = getattr(self, f"handle_{self.mode}")
        return handler(pil_image, **kwargs)


# @adapter(IWantImageTransforming)
# @implementer(IImageTransformer)
class OriginalFocalPointsTransformer(BaseImageTransformer):
    """Determine focalpoints on the original while saving an image."""

    def handle_original(self, pil_image, **kwargs):
        # Adapted mostly from transformer.do_smart_detection
        focal_points = []
        # Future: call named adapters that determine various focal points,
        # for example one for features, one for faces.
        # order does not matter here
        # for name, handler in getAdapters((obj,), IFocalPointDetector):
        for handler in (FeatureFocalpointDetector(self.context),):
            found = handler(pil_image)
            if found:
                focal_points.extend(found)
        if not focal_points:
            # Clear a previously determined focal point.
            logger.debug("No focal points found.")
            self.field.focal_point = None
            return
        logger.debug("Found focal points: %r", focal_points)
        focal_x, focal_y = self.get_center_of_mass(focal_points)
        logger.debug("Center of mass: %d, %d", focal_x, focal_y)
        # Save the focal point information on the field.
        self.field.focal_point = (focal_x, focal_y)

    def get_center_of_mass(self, focal_points):
        # From transformer.get_center_of_mass
        total_weight = 0.0
        total_x = 0.0
        total_y = 0.0

        for focal_point in focal_points:
            total_weight += focal_point.weight

            total_x += focal_point.x * focal_point.weight
            total_y += focal_point.y * focal_point.weight

        avg_x = round(total_x // total_weight)
        avg_y = round(total_y // total_weight)

        return avg_x, avg_y


# @adapter(IWantImageTransforming)
# @implementer(IImageTransformer)
class CropFocalPointsTransformer(BaseImageTransformer):
    """Crop using already determined focal points.

    We handle modes 'contain' and 'cover'. (Mode 'scale' needs no cropping.)
    Technically they are not the same, but the difference is too subtle for me.
    I am assuming with the focal points the outcome will be fine in both cases.
    """

    def prepare(self, field, mode, **kwargs):
        super().prepare(field, mode, **kwargs)
        if not self.available:
            return
        if not getattr(field, "focal_point", None):
            self.available = False
            return

    def handle_contain(self, pil_image, target_width, target_height, **kwargs):
        """Handle mode/direction: contain, scale-crop-to-fit, down

        From
        https://github.com/plone/plone.scale/blob/0326149525ec8a39b8f74506c67b15c5aa6801c1/plone/scale/scale.py#L320-L352

        `contain`
        Alternative spellings: `scale-crop-to-fit`, `down`.
        Starts by scaling the smallest dimension to the required
        size and crops the other dimension if needed.

        'Smallest dimension' seems to mean: the axis that needs the least scaling.
        So scale the original image up or down until either width or height is the same
        as the target width or height.
        Then crop the extraneous part of the other axis.
        """
        return self.crop(pil_image, target_width, target_height, **kwargs)

    def _unused_handle_cover(self, pil_image, target_width, target_height, **kwargs):
        """Handle mode/direction: cover, scale-crop-to-fill, up

         From
         https://github.com/plone/plone.scale/blob/0326149525ec8a39b8f74506c67b15c5aa6801c1/plone/scale/scale.py#L320-L352

        `cover`
         Alternative spellings: `scale-crop-to-fill`, `up`.
         Starts by scaling the largest dimension up to the required size
         and crops the other dimension if needed.

         At the moment I treat this the same as 'contain' though.

         Actually, in standard Plone, I see no difference between cover and scale.
         Maybe with very small images that need to be scaled up?
         Ah, indeed:
         - cover can scale up.  I see no evidence of cropping though.
           Could be an error, but it seems to fit the description.
           Remember, I am talking about standard Plone.
         - scale does not scale up, only down

         Is there any way with focal points that we can make this mode meaningful?
         I suppose not.
         The upscaling could still be useful.
         But it seems best to let standard Plone handle this mode.
        """
        return self.crop(pil_image, target_width, target_height, **kwargs)

    def crop(self, pil_image, target_width, target_height, **kwargs):
        # Adapted from transformer.auto_crop

        # Avoid 0px images.
        target_width = int(target_width) or 1
        target_height = int(target_height) or 1

        source_width, source_height = pil_image.size

        source_ratio = round(source_width / source_height, 2)
        target_ratio = round(target_width / target_height, 2)

        if source_ratio == target_ratio:
            return

        focal_x, focal_y = self.field.focal_point
        if target_width / source_width > target_height / source_height:
            # We can keep the entire source width during cropping.
            crop_left = 0
            crop_right = crop_width = source_width
            crop_height = int(round(source_width * target_height / target_width, 0))
            crop_top = int(
                round(
                    min(
                        max(focal_y - (crop_height / 2), 0.0),
                        source_height - crop_height,
                    )
                )
            )
            crop_bottom = min(crop_top + crop_height, source_height)
        else:
            # We can keep the entire source height during cropping.
            # Note to self: top left corner is at (0, 0).
            crop_top = 0
            crop_bottom = crop_height = source_height
            crop_width = int(
                round(
                    math.ceil(target_width * source_height / target_height),
                    0,
                )
            )
            crop_left = int(
                round(
                    min(
                        max(focal_x - (crop_width / 2), 0.0),
                        source_width - crop_width,
                    )
                )
            )
            crop_right = min(crop_left + crop_width, source_width)

        logger.debug(
            f"Cropping image: {crop_left}, {crop_top}, {crop_right}, {crop_bottom}"
        )
        pil_image = pil_image.crop((crop_left, crop_top, crop_right, crop_bottom))
        # Now resize.
        logger.debug(f"Resizing image to {target_width}x{target_height}")
        pil_image.draft(pil_image.mode, (target_width, target_height))
        # Resize creates a new image.
        new_image = pil_image.resize((target_width, target_height), PIL.Image.ANTIALIAS)
        return new_image
