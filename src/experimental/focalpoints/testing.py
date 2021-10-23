# -*- coding: utf-8 -*-
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import (
    PLONE_FIXTURE,
    FunctionalTesting,
    IntegrationTesting,
    PloneSandboxLayer,
    applyProfile,
)
from plone.testing import z2

import experimental.focalpoints


class ExperimentalFocalpointsLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load any other ZCML that is required for your tests.
        # The z3c.autoinclude feature is disabled in the Plone fixture base
        # layer.
        import plone.app.dexterity

        self.loadZCML(package=plone.app.dexterity)
        import plone.restapi

        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=experimental.focalpoints)

    def setUpPloneSite(self, portal):
        applyProfile(portal, "experimental.focalpoints:default")


EXPERIMENTAL_FOCALPOINTS_FIXTURE = ExperimentalFocalpointsLayer()


EXPERIMENTAL_FOCALPOINTS_INTEGRATION_TESTING = IntegrationTesting(
    bases=(EXPERIMENTAL_FOCALPOINTS_FIXTURE,),
    name="ExperimentalFocalpointsLayer:IntegrationTesting",
)


EXPERIMENTAL_FOCALPOINTS_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(EXPERIMENTAL_FOCALPOINTS_FIXTURE,),
    name="ExperimentalFocalpointsLayer:FunctionalTesting",
)


EXPERIMENTAL_FOCALPOINTS_ACCEPTANCE_TESTING = FunctionalTesting(
    bases=(
        EXPERIMENTAL_FOCALPOINTS_FIXTURE,
        REMOTE_LIBRARY_BUNDLE_FIXTURE,
        z2.ZSERVER_FIXTURE,
    ),
    name="ExperimentalFocalpointsLayer:AcceptanceTesting",
)
