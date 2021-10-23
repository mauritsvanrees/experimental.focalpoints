# from .interfaces import IImageTransformer
from .interfaces import IWantImageTransforming
from .transformer import OriginalFocalPointsTransformer
from .utils import determine_focalpoint_for_image
from plone.dexterity.utils import iterSchemata
from plone.namedfile.interfaces import INamedImageField
from zope.component import adapter
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.schema import getFieldsInOrder

import logging


logger = logging.getLogger(__name__)


def get_image_field_values(obj, first=False):
    """Get all image fields values.

    When 'first' is True, we return the first one.
    This can be useful in code wants to know if any image field is filled.
    """
    fields = []
    for schema in iterSchemata(obj):
        adapter = schema(obj)
        for name, field in getFieldsInOrder(schema):
            if INamedImageField.providedBy(field):
                value = getattr(adapter, name)
                if value:
                    if first:
                        return value
                    fields.append(value)
    return fields


def determine_focalpoints(obj):
    # Gather all image fields.
    field_values = get_image_field_values(obj)
    if not field_values:
        return
    # Future: use getAdapters on IImageTransformer to get all.
    transformer = OriginalFocalPointsTransformer(obj)
    for field_value in field_values:
        determine_focalpoint_for_image(field_value, transformer=transformer)


@adapter(IWantImageTransforming, IObjectAddedEvent)
def content_added(obj, event):
    determine_focalpoints(obj)


@adapter(IWantImageTransforming, IObjectModifiedEvent)
def content_modified(obj, event):
    determine_focalpoints(obj)
