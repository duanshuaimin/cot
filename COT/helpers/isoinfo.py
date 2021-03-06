#!/usr/bin/env python
#
# isoinfo.py - Helper for 'isoinfo'
#
# September 2016, Glenn F. Matthews
# Copyright (c) 2016-2017 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Give COT access to isoinfo for inspecting ISO images.

http://cdrecord.org/
"""

from .helper import Helper


class ISOInfo(Helper):
    """Helper provider for ``isoinfo``.

    http://cdrecord.org/
    """

    _provider_package = {
        'apt-get': 'genisoimage',
        'brew': 'cdrtools',
        'port': 'cdrtools',
    }

    def __init__(self):
        """Initializer."""
        super(ISOInfo, self).__init__(
            "isoinfo",
            info_uri="http://cdrecord.org",
            version_regexp=r"isoinfo ([0-9.]+)")
