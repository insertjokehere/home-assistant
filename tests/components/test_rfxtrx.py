"""Th tests for the Rfxtrx component."""
# pylint: disable=too-many-public-methods,protected-access
import unittest
import time

from homeassistant.components import rfxtrx as rfxtrx
from homeassistant.components.switch import rfxtrx as rfxtrx_switch
from homeassistant.components.sensor import rfxtrx as rfxtrx_sensor
from homeassistant.components.rfxtrx import (
    ATTR_FIREEVENT, ATTR_NAME, ATTR_PACKETID, ATTR_STATE, EVENT_BUTTON_PRESSED)

from tests.common import get_test_home_assistant
from unittest.mock import patch

class TestRFXTRX(unittest.TestCase):
    """Test the Rfxtrx component."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant(0)

    def tearDown(self):
        """Stop everything that was started."""
        rfxtrx.RECEIVED_EVT_SUBSCRIBERS = []
        rfxtrx.RFX_DEVICES = {}
        if rfxtrx.RFXOBJECT:
            rfxtrx.RFXOBJECT.close_connection()
        self.hass.stop()

    def test_default_config(self):
        """Test configuration."""
        self.assertTrue(rfxtrx.setup(self.hass, {
            'rfxtrx': {
                'device': '/dev/serial/by-id/usb' +
                          '-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0',
                'dummy': True}
        }))

        config = {'devices': {}}
        devices = []

        def add_dev_callback(devs):
            """Add a callback to add devices."""
            for dev in devs:
                devices.append(dev)

        rfxtrx_sensor.setup_platform(self.hass, config, add_dev_callback)

        while len(rfxtrx.RFX_DEVICES) < 2:
            time.sleep(0.1)

        self.assertEquals(len(rfxtrx.RFXOBJECT.sensors()), 2)
        self.assertEquals(len(devices), 2)

    def test_config_failing(self):
        """Test configuration."""
        self.assertFalse(rfxtrx.setup(self.hass, {
            'rfxtrx': {}
        }))

    def test_fire_event(self):
        """Test fire event."""
        self.assertTrue(rfxtrx.setup(self.hass, {
            'rfxtrx': {
                'device': '/dev/serial/by-id/usb' +
                          '-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0',
                'dummy': True}
        }))

        devices = []
        calls = []
        config = {'automatic_add': True, 'devices':
                  {'123efab1': {
                      'name': 'Test',
                      'packetid': '0b1100cd0213c7f210010f51',
                      ATTR_FIREEVENT: True}}}
        import RFXtrx as rfxtrxmod
        rfxtrx.RFXOBJECT =\
            rfxtrxmod.Core("", transport_protocol=rfxtrxmod.DummyTransport)

        devices = []

        def add_dev_callback(devs):
            """Add a callback to add devices."""
            for dev in devs:
                devices.append(dev)

        def record_event(event):
            """Add recorded event to set."""
            calls.append(event)

        from homeassistant.const import MATCH_ALL

        self.hass.bus.listen(MATCH_ALL, record_event)

        rfxtrx_switch.setup_platform(self.hass, config, add_dev_callback)

        self.assertEqual(1, len(devices))
        entity = devices[0]
        self.assertEqual('Test', entity.name)
        self.assertEqual('off', entity.state)
        self.assertTrue(entity.should_fire_event)

        event = rfxtrx.get_rfx_object('0b1100cd0213c7f210010f51')
        event.data = bytearray([0x0b, 0x11, 0x00, 0x10, 0x01, 0x18,
                                0xcd, 0xea, 0x01, 0x01, 0x0f, 0x70])
        with patch('homeassistant.components.switch.' +
                   'rfxtrx.RfxtrxSwitch.update_ha_state',
                   return_value=None):
            rfxtrx.RECEIVED_EVT_SUBSCRIBERS[0](event)
        entity = devices[1]
        entity._should_fire_event = True
        with patch('homeassistant.components.switch.' +
                   'rfxtrx.RfxtrxSwitch.update_ha_state',
                   return_value=None):
            rfxtrx.RECEIVED_EVT_SUBSCRIBERS[0](event)

        self.assertEqual(event.values['Command'], "On")
        self.assertTrue(entity.should_fire_event)
        self.assertEqual(2, len(rfxtrx.RFX_DEVICES))
        self.assertEqual(2, len(devices))
        self.assertEqual(1, len(calls))
