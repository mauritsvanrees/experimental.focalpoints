from .transformer import OriginalFocalPointsTransformer

import logging
import PIL.Image


logger = logging.getLogger(__name__)


def determine_focalpoint_for_image(field_value, transformer=None, context=None):
    if transformer is None:
        # At the moment, the context for the transformer does not matter.
        # But theoretically, we may have a Portrait portal_type where we
        # want face detection, and a Cake portal_type where we want
        # feature detection.
        if context is None:
            context = field_value
        transformer = OriginalFocalPointsTransformer(context)
    transformer.prepare(field_value, "original")
    if not transformer.available:
        return
    with field_value.open() as image_file:
        try:
            pil_image = PIL.Image.open(image_file)
        except OSError:
            # Probably: cannot identify image file
            # Locally I have experimental.gracefulblobmissing,
            # so image blobs may be wrong.
            logger.warning("OSError opening image file at %s", transformer.context)
            return
        transformer.run(pil_image)
