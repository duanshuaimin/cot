#!/usr/bin/env python
#
# inject_config.py - Implements "cot inject-config" command
#
# February 2014, Glenn F. Matthews
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

"""Implements "inject-config" command."""

import logging
import os.path
import shutil

from COT.add_disk import add_disk_worker
from COT.data_validation import ValueUnsupportedError, InvalidInputError
from COT.disks import create_disk
from COT.submodule import COTSubmodule

logger = logging.getLogger(__name__)


class COTInjectConfig(COTSubmodule):
    """Wrap configuration file(s) into a disk image embedded into the VM.

    Inherited attributes:
    :attr:`~COTGenericSubmodule.ui`,
    :attr:`~COTSubmodule.package`,
    :attr:`~COTSubmodule.output`

    Attributes:
    :attr:`config_file`,
    :attr:`secondary_config_file`,
    :attr:`extra_files`
    """

    def __init__(self, ui):
        """Instantiate this submodule with the given UI.

        Args:
          ui (UI): User interface instance.
        """
        super(COTInjectConfig, self).__init__(ui)
        self._config_file = None
        self._secondary_config_file = None
        self._extra_files = []

    @property
    def config_file(self):
        """Primary configuration file.

        Raises:
          InvalidInputError: if the file does not exist
          InvalidInputError: if the platform described by :attr:`package`
              doesn't support configuration files.
        """
        return self._config_file

    @config_file.setter
    def config_file(self, value):
        if value is not None:
            value = str(value)
            if not os.path.exists(value):
                raise InvalidInputError("Primary config file {0} not found!"
                                        .format(value))
            if not self.vm.platform.CONFIG_TEXT_FILE:
                raise InvalidInputError(
                    "Configuration file not supported for platform {0}"
                    .format(self.vm.platform.__name__))
        self._config_file = value

    @property
    def secondary_config_file(self):
        """Secondary configuration file.

        Raises:
          InvalidInputError: if the file does not exist
          InvalidInputError: if the platform described by :attr:`package`
              doesn't support secondary configuration files.
        """
        return self._secondary_config_file

    @secondary_config_file.setter
    def secondary_config_file(self, value):
        if value is not None:
            value = str(value)
            if not os.path.exists(value):
                raise InvalidInputError("Secondary config file {0} not found!"
                                        .format(value))
            if not self.vm.platform.SECONDARY_CONFIG_TEXT_FILE:
                raise InvalidInputError(
                    "Secondary configuration file not supported "
                    "for platform {0}".format(self.vm.platform.__name__))
        self._secondary_config_file = value

    @property
    def extra_files(self):
        """Additional files to be embedded as-is.

        Raises:
          InvalidInputError: if any file in the list does not exist
        """
        return self._extra_files

    @extra_files.setter
    def extra_files(self, values):
        for path in values:
            if not os.path.exists(path):
                raise InvalidInputError("File {0} not found!".format(path))
        self._extra_files = values

    def ready_to_run(self):
        """Check whether the module is ready to :meth:`run`.

        Returns:
          tuple: ``(True, ready_message)`` or ``(False, reason_why_not)``
        """
        if not (self.config_file or
                self.secondary_config_file or
                self.extra_files):
            return False, "No files specified - nothing to do!"
        return super(COTInjectConfig, self).ready_to_run()

    def run(self):
        """Do the actual work of this submodule.

        Raises:
          InvalidInputError: if :func:`ready_to_run` reports ``False``
          ValueUnsupportedError: if the
              :const:`~COT.platforms.GenericPlatform.BOOTSTRAP_DISK_TYPE` of
              the associated VM's
              :attr:`~COT.vm_description.VMDescription.platform` is not
              'cdrom' or 'harddisk'
          LookupError: if unable to find a disk drive device to inject
              the configuration into.
        """
        super(COTInjectConfig, self).run()

        vm = self.vm

        platform = vm.platform

        # Find the disk drive where the config should be injected
        # First, look for any previously-injected config disk to overwrite:
        if platform.BOOTSTRAP_DISK_TYPE == 'cdrom':
            (f, _, _, drive_device) = vm.search_from_filename('config.iso')
        elif platform.BOOTSTRAP_DISK_TYPE == 'harddisk':
            (f, _, _, drive_device) = vm.search_from_filename('config.vmdk')
        else:
            raise ValueUnsupportedError("bootstrap disk drive type",
                                        platform.BOOTSTRAP_DISK_TYPE,
                                        "'cdrom' or 'harddisk'")
        if f is not None:
            file_id = vm.get_id_from_file(f)
            self.ui.confirm_or_die(
                "Existing configuration disk '{0}' found.\n"
                "Continue and overwrite it?".format(file_id))
            logger.warning("Overwriting existing config disk '%s'", file_id)
        else:
            file_id = None
            # Find the empty slot where we should inject the config
            drive_device = vm.find_empty_drive(platform.BOOTSTRAP_DISK_TYPE)

        if drive_device is None:
            raise LookupError("Could not find an empty {0} drive to "
                              "inject the config into"
                              .format(platform.BOOTSTRAP_DISK_TYPE))
        (cont_type, drive_address) = vm.find_device_location(drive_device)

        # Copy config file(s) to per-platform name in working directory
        config_files = []
        if self.config_file:
            dest = os.path.join(vm.working_dir, platform.CONFIG_TEXT_FILE)
            shutil.copy(self.config_file, dest)
            config_files.append(dest)
        if self.secondary_config_file:
            dest = os.path.join(vm.working_dir,
                                platform.SECONDARY_CONFIG_TEXT_FILE)
            shutil.copy(self.secondary_config_file, dest)
            config_files.append(dest)

        # Extra files are packaged as-is
        config_files += self.extra_files

        # Package the config files into a disk image
        # pylint:disable=redefined-variable-type
        if platform.BOOTSTRAP_DISK_TYPE == 'cdrom':
            bootstrap_file = os.path.join(vm.working_dir, 'config.iso')
            disk_image = create_disk(disk_format='iso',
                                     path=bootstrap_file,
                                     files=config_files)
        elif platform.BOOTSTRAP_DISK_TYPE == 'harddisk':
            bootstrap_file = os.path.join(vm.working_dir, 'config.img')
            disk_image = create_disk(disk_format='raw',
                                     path=bootstrap_file,
                                     files=config_files)
        else:
            raise ValueUnsupportedError("bootstrap disk drive type",
                                        platform.BOOTSTRAP_DISK_TYPE,
                                        "'cdrom' or 'harddisk'")

        # Inject the disk image into the OVA, using "add-disk" functionality
        add_disk_worker(
            ui=self.ui,
            vm=vm,
            disk_image=disk_image,
            drive_type=platform.BOOTSTRAP_DISK_TYPE,
            file_id=file_id,
            controller=cont_type,
            address=drive_address,
            subtype=None,
            description='Configuration disk',
            diskname=None,
        )

    def create_subparser(self):
        """Create 'inject-config' CLI subparser."""
        p = self.ui.add_subparser(
            'inject-config',
            aliases=['add-bootstrap'],
            help="Inject a configuration file into an OVF package",
            usage=self.ui.fill_usage("inject-config", [
                "PACKAGE [-o OUTPUT] [-c CONFIG_FILE] "
                "[-s SECONDARY_CONFIG_FILE] [-e EXTRA_FILE [EXTRA_FILE2 ...]]",
            ]),
            description="""
Add one or more "bootstrap" configuration file(s) to the given OVF or OVA.
These files will be packaged into a virtual hard disk, or virtual CD-ROM,
as appropriate to the target platform. Any specified primary and secondary
config files will be renamed if necessary to meet expectations of the target
platform, while any files provided with the --extra-files option will
be included as-is and will not be renamed.""")

        p.add_argument('-o', '--output',
                       help="Name/path of new VM package to create "
                       "instead of updating the existing package")

        p.add_argument('-c', '--config-file',
                       help="Text file to embed as primary configuration")
        p.add_argument('-s', '--secondary-config-file',
                       help="Text file to embed as secondary configuration"
                       " (currently only used for IOS XR admin config)")
        p.add_argument('-e', '--extra-files', action='append', nargs='+',
                       metavar=('EXTRA_FILE', 'EXTRA_FILE2'),
                       help="Additional file(s) to include as-is")
        p.add_argument('PACKAGE',
                       help="Package, OVF descriptor or OVA file to edit")
        p.set_defaults(instance=self)
