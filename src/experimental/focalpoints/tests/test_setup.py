# -*- coding: utf-8 -*-
"""Setup tests for this package."""
import unittest

from plone import api
from plone.app.testing import TEST_USER_ID, setRoles

from experimental.focalpoints.testing import (  # noqa: E501
    EXPERIMENTAL_FOCALPOINTS_INTEGRATION_TESTING,
)

try:
    from Products.CMFPlone.utils import get_installer
except ImportError:
    get_installer = None


class TestSetup(unittest.TestCase):
    """Test that experimental.focalpoints is properly installed."""

    layer = EXPERIMENTAL_FOCALPOINTS_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")

    def test_product_installed(self):
        """Test if experimental.focalpoints is installed."""
        self.assertTrue(self.installer.is_product_installed("experimental.focalpoints"))

    def test_browserlayer(self):
        """Test that IExperimentalFocalpointsLayer is registered."""
        from plone.browserlayer import utils

        from experimental.focalpoints.interfaces import IExperimentalFocalpointsLayer

        self.assertIn(IExperimentalFocalpointsLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = EXPERIMENTAL_FOCALPOINTS_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        if get_installer:
            self.installer = get_installer(self.portal, self.layer["request"])
        else:
            self.installer = api.portal.get_tool("portal_quickinstaller")
        roles_before = api.user.get_roles(TEST_USER_ID)
        setRoles(self.portal, TEST_USER_ID, ["Manager"])
        self.installer.uninstall_product("experimental.focalpoints")
        setRoles(self.portal, TEST_USER_ID, roles_before)

    def test_product_uninstalled(self):
        """Test if experimental.focalpoints is cleanly uninstalled."""
        self.assertFalse(
            self.installer.is_product_installed("experimental.focalpoints")
        )

    def test_browserlayer_removed(self):
        """Test that IExperimentalFocalpointsLayer is removed."""
        from plone.browserlayer import utils

        from experimental.focalpoints.interfaces import IExperimentalFocalpointsLayer

        self.assertNotIn(IExperimentalFocalpointsLayer, utils.registered_layers())
