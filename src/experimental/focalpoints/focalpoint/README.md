# Focal point detection

We can transform images.
There may be various transforms available.
There may also be various focal point detectors: for features, for faces, etcetera.

Idea for the future: do this with named adapters.
The adapter classes can have an 'order' attribute that we can sort on.
That is how transforms like plone.app.theming and plone.protect are called in the same order.

Some stages that can be done to the original:

- Change the image size, mostly making it smaller (no 25 MB original images please).
- Change the format, for example TIFF to jpeg. [`plone.scale.scale.scaleImage`](https://github.com/plone/plone.scale/blob/3.1.2/plone/scale/scale.py#L58-L66) does this when scaling, but could be done for the original as well.
- Convert to simpler mode if possible, see [plone.scale again](https://github.com/plone/plone.scale/blob/3.1.2/plone/scale/scale.py#L71-L89), which does this right after scaling though.
- various focal point detectors
- combine all focal points into one x-y coordinate
- Delete old scales.

That can be done when an image is added or modified.

Some stages that can be done when scaling/cropping:

- Several of the above
- determine target width and height?
- Set image quality
- srcset information
- scale (duh)
- crop, applying focal point information
- standard crop

Probably we should pass keyword arguments around
- Transformer 1 receives keyword arguments and returns None.
- The same keyword arguments are passed to Transformer 2.
- Transformer 2 pops one kw and adds a few others.
- The updated kws are passed to transformer 3.

```
class BaseImageTransformer:
    # Transforms are ordered, lowest number is run first.
    order = 5000
    # By default this transformer is available,
    # but 'prepare' can set it to False.
    available = True

    def __init__(self, context):
        self.context = context

    def prepare(self, field, mode, **kwargs):
        self.field = field
        self.mode = mode
        if not field.size:
            self.available = False
            return
        if not hasattr(self, f"handle_{mode}", None):
            self.available = False
            return
        self.image = PIL.Image.open(field.data)
        # Sub classes would call super.prepare plus some own stuff.
        # For example: set an attribute self.focal_points
        # that you get from the field.
        pass

    def run(self, **kwargs):
        handler = getattr(self, f"handle_{mode}")
        return handler(**kwargs)

```

## Focal points

How would we do focal points with the above ideas?

Register an **event handler for object modified** event on dexterity content.
Let this go over all image transformers.
Code is similar to plone.transformchain.transformer.

```
from zope.component import getAdapters

def _order_getter(pair):
    return pair[1].order

def call_image_transforms(obj, field):
    handlers = sorted(
        getAdapters((obj), IImageTransformer),
        key=_order_getter
    )
    for name, handler in handlers:
        handler.prepare(field, "original")
        if handler.available:
            handler.run()

```

Register a transformer to determine a feature focal point.

```
class FeatureFocalPointsTransformer(BaseImageTransformer):

    def handle_original(self, **kwargs):
        ... detect focal points
        ... add them to existing list of focal points
        self.field.focal_points.append(...)
        # But the first one should empty the list,
        # so either create yet another transformer,
        # or turn the focal point detection
        # into its own transform chain.

```

Possibly register another transformer for face detection.
Not relevant for our current customer though:

Register a transformer to determine the center of mass of all focal points.

```
class CombineFocalPointsTransformer(BaseImageTransformer):

    def handle_original(self, **kwargs):
        self.field.focal_x, self.field.focal_y = self.get_center_of_mass(
            self.field.focal_points)
```

What could a **separate transform chain for focal points** look like?

```
class OriginalFocalPointsTransformer(BaseImageTransformer):

    def handle_original(self, **kwargs):
        focal_points = []
        # order does not matter here
        for name, handler in getAdapters((obj,), IFocalPointDetector):
            found = handler(self.image)
            if found:
                focal_points.append(found)
        self.field.focal_x, self.field.focal_y = self.get_center_of_mass(focal_points)
```

That may be easier.

Anyway, the above takes care of storing the focal point on the original image.
Now we need to hook into **creating scales**.

The hook needs to be in `plone.namedfile.scaling.DefaultImageScalingFactory` in a method which is actually really small:

```
    def create_scale(self, data, direction, height, width, **parameters):
        return scaleImage(
            data, direction=direction, height=height, width=width, **parameters
        )
```

Well, alternatively we could hook into the called `plone.scale.scale.scaleImage`.
This is a function, so we cannot override parts of it.
It does useful things which could be done in a new transform chain, like imagined above.
The most important stuff happens in this line:

```
image = scalePILImage(image, width, height, mode, direction=direction)
```

This function has:

```
# Do potentially useful conversions,
# like black/white, CMYK/RGB.
mode = get_scale_mode(mode, direction)
if mode == 'scale':
    return _scale_thumbnail(image, width, height)
dimensions = _calculate_all_dimensions(...)
if dimensions.factor_height == dimensions.factor_width:
    # The original already has the right aspect ratio,
    # so we only need to scale.
    if mode == 'contain':
        image.thumbnail(...)
        return image
    return image.resize(...)
# Do cropping with combinations of
# image.draft/resize/crop.
```

So... which one do we override for now?

- scaleImage is imported by plone.app.tiles.imagescaling and plone.namedfile.scaling
- scalePILImage is defined and used only in plone.scale.scale

scalePILImage it is then.

```
def scalePILImage(image, width=None, height=None, mode='contain', direction=None):
    mode = get_scale_mode(mode, direction)
    if mode == "scale":
        return orig_scalePILImage(image, width, height, mode, direction=direction)
    # We cannot do this call, because we we do not have the object:
    # getAdapters((obj, field), IImageTransformer)
    # So this is not the right place for an image transform chain.
    # We could register adapters only for the image.
    # Not chance then to restrict this to only one portal_type though.
    ... Do something with the found focus points here.
```

But: the focus points are stored on the field, and we do not have it here.
So it isn't going to work.
Same is true for the scaleImage function.
So we override the create_scale method in `plone.namedfile.scaling.DefaultImageScalingFactory`

## Focal points now

For our customer on the short term, we don't have to do it quite like this, it can be easier.

- Register an **event handler for object modified** event on dexterity content.
- This calls OriginalFocalPointsTransformer.handle_original from above, but without the adapters.
- Override `plone.namedfile.scaling.DefaultImageScalingFactory.create_scale`.
- When `mode=scale` call the original `create_scale`.
- Otherwise call our focal point cropping methods.
