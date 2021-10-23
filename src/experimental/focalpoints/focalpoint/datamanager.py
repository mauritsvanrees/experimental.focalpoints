from .utils import determine_focalpoint_for_image
from plone.namedfile.interfaces import INamedBlobImageField
from z3c.form import datamanager
from zope.component import adapter
from zope.interface import Interface


@adapter(Interface, INamedBlobImageField)
class AttributeImageField(datamanager.AttributeField):
    """Data manager for image field in an attribute.

    The original is registered for any field, via zope.schema.interfaces.IField.
    A field in an attribute means: a field on a content item in a schema
    or behavior.

    Technically we might want to register this adapter for INamedImageField,
    so the non-blob version, which INamedBlobImageField inherits from.
    But that seems a special case which should hardly occur.
    And it might need different code when opening images.
    So never mind.
    """

    def set(self, value):
        """See z3c.form.interfaces.IDataManager"""
        if self.field.readonly:
            raise TypeError(
                "Can't set values on read-only fields "
                "(name=%s, class=%s.%s)"
                % (
                    self.field.__name__,
                    self.context.__class__.__module__,
                    self.context.__class__.__name__,
                )
            )
        if value is not None:
            # Note: the context does not matter currently, but this could change.
            determine_focalpoint_for_image(value, context=self.adapted_context)
        super(AttributeImageField, self).set(value)


@adapter(dict, INamedBlobImageField)
class DictionaryImageField(datamanager.DictionaryField):
    """Data manager for image field in a dictionary.

    The original is registered for any field, via zope.schema.interfaces.IField.
    A field in a dictionary means: a field in tile data.
    """

    def set(self, value):
        """See z3c.form.interfaces.IDataManager"""
        if self.field.readonly:
            raise TypeError(
                "Can't set values on read-only fields name=%s" % self.field.__name__
            )
        if value is not None:
            determine_focalpoint_for_image(value)
        super(DictionaryImageField, self).set(value)
