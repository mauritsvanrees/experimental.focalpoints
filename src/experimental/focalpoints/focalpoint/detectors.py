from .point import FocalPoint

import cv2
import logging
import numpy as np


logger = logging.getLogger(__name__)


class BaseFocalpointDetector:
    def __init__(self, context):
        self.context = context


class FeatureFocalpointDetector(BaseFocalpointDetector):
    # Weight of the focal point.
    weight = 1.0

    def __call__(self, pil_image):
        # Adapted from thumbor.detectors.feature_detector.__init__.py
        try:
            # Convert to gray scale:
            pil_image = pil_image.convert("L")
            # Note: we need a numpy array as input for cv2
            img = np.array(pil_image)
        except Exception as error:
            logger.exception(error)
            logger.warning("Error during feature detection.")
            return

        points = cv2.goodFeaturesToTrack(
            img,
            maxCorners=20,
            qualityLevel=0.04,
            minDistance=1.0,
            useHarrisDetector=False,
        )
        if points is None:
            return
        focal_points = []
        for point in points:
            x_pos, y_pos = point.ravel()
            focal_points.append(FocalPoint(x_pos.item(), y_pos.item(), self.weight))
        return focal_points
