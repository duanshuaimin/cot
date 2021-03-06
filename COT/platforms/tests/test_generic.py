# test_generic_platform.py - Unit test cases for COT "generic platform"
#
# October 2016, Glenn F. Matthews
# Copyright (c) 2014-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the GenericPlatform class."""

import unittest
from COT.platforms.generic import GenericPlatform
from COT.data_validation import ValueTooLowError


class TestGenericPlatform(unittest.TestCase):
    """Test cases for generic platform handling."""

    cls = GenericPlatform

    def test_controller_type_for_device(self):
        """Test platform-specific logic for device controllers."""
        self.assertEqual(self.cls.controller_type_for_device('harddisk'),
                         'ide')
        self.assertEqual(self.cls.controller_type_for_device('cdrom'),
                         'ide')

    def test_nic_name(self):
        """Test NIC name construction."""
        self.assertEqual(self.cls.guess_nic_name(1), "Ethernet1")
        self.assertEqual(self.cls.guess_nic_name(100), "Ethernet100")

    def test_cpu_count(self):
        """Test CPU count limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_cpu_count, 0)
        self.cls.validate_cpu_count(1)

    def test_memory_amount(self):
        """Test RAM allocation limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_memory_amount, 0)
        self.cls.validate_memory_amount(1)

    def test_nic_count(self):
        """Test NIC range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_nic_count, -1)
        self.cls.validate_nic_count(0)

    def test_serial_count(self):
        """Test serial port range limits."""
        self.assertRaises(ValueTooLowError, self.cls.validate_serial_count, -1)
        self.cls.validate_serial_count(0)
