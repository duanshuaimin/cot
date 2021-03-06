#!/usr/bin/env python
#
# test_cli.py - Unit test cases for generic COT CLI.
#
# September 2013, Glenn F. Matthews
# Copyright (c) 2013-2016 the COT project developers.
# See the COPYRIGHT.txt file at the top-level directory of this distribution
# and at https://github.com/glennmatthews/cot/blob/master/COPYRIGHT.txt.
#
# This file is part of the Common OVF Tool (COT) project.
# It is subject to the license terms in the LICENSE.txt file found in the
# top-level directory of this distribution and at
# https://github.com/glennmatthews/cot/blob/master/LICENSE.txt. No part
# of COT, including this file, may be copied, modified, propagated, or
# distributed except according to the terms contained in the LICENSE.txt file.

"""Unit test cases for the COT.cli.CLI class and related functionality."""

from __future__ import print_function

import logging
import os
import os.path
import sys

try:
    import StringIO
except ImportError:
    import io as StringIO

import mock

from COT import __version_long__
from COT.tests.ut import COT_UT
from COT.cli import CLI
from COT.data_validation import InvalidInputError

# pylint: disable=missing-param-doc,missing-type-doc


class TestCOTCLI(COT_UT):
    """Parent class for CLI test cases."""

    @staticmethod
    def creating_network_warning(net_name):
        """Warning log message for creating a new network entry.

        Args:
          net_name (str): Name of new network
        Returns:
          dict: kwargs suitable for passing into :meth:`assertLogged`
        """
        return {
            'levelname': 'WARNING',
            'msg': "Automatically agreeing to '%s'",
            'args': ("Network {0} is not currently defined. Create it?"
                     .format(net_name), ),
        }

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        self.cli = CLI(terminal_width=80)
        self.maxDiff = None
        super(TestCOTCLI, self).setUp()

    def tearDown(self):
        """Test case cleanup function called automatically after each test."""
        # If we set the verbosity of the CLI directly, the CLI logger is on.
        # The CLI normally turns the logger back off at the end of cli.main()
        # but in some of our CLI test cases we don't call cli.main(), so
        # to prevent leakage of logs, we clean up manually if needed.
        if self.cli.master_logger:
            self.cli.master_logger.removeHandler(self.cli.handler)
            self.cli.master_logger = None
            self.cli.handler.close()
            self.cli.handler = None
        super(TestCOTCLI, self).tearDown()

    def set_terminal_width(self, width):
        """Modify the width of the virtual terminal."""
        self.cli._terminal_width = width  # pylint: disable=protected-access

    def call_cot(self, argv, result=0, fixup_args=True):
        """Invoke COT CLI, capturing stdout and stderr, and check the rc.

        In the case of an incorrect rc, the test will fail.
        Otherwise, will return the combined stdout/stderr.
        """
        rc = -1
        if fixup_args:
            argv = ['--quiet'] + argv

        # Python 2.6 doesn't let us mock multiple times in one 'with'
        with mock.patch('sys.stdin'):
            with mock.patch('sys.stdout',
                            new_callable=StringIO.StringIO) as _so:
                with mock.patch('sys.stderr',
                                new_callable=StringIO.StringIO) as _se:
                    try:
                        rc = self.cli.run(argv)
                    except SystemExit as se:
                        try:
                            rc = int(se.code)
                        except (TypeError, ValueError):
                            print(se.code, file=sys.stderr)
                            rc = 1
                    stdout = _so.getvalue()
                    stderr = _se.getvalue()

        self.assertEqual(rc, result,
                         "\nargv: \n{0}\nstdout:\n{1}\nstderr:\n{2}"
                         .format(" ".join(argv), stdout, stderr))
        return stdout


class TestCLIModule(TestCOTCLI):
    """Test cases for the CLI module itself."""

    def setUp(self):
        """Test case setup function called automatically prior to each test."""
        super(TestCLIModule, self).setUp()
        self.first_call = True

    def test_apis_without_force(self):
        """Test confirm, confirm_or_die, etc. without --force option."""
        self.cli.force = False

        self.cli.input = lambda _: 'y'
        self.assertTrue(self.cli.confirm("prompt"))
        self.cli.confirm_or_die("prompt")

        self.cli.input = lambda _: 'n'
        self.assertFalse(self.cli.confirm("prompt"))
        self.assertRaises(SystemExit, self.cli.confirm_or_die, "prompt")

        self.cli.input = lambda _: 'hello'
        self.assertEqual("hello", self.cli.get_input("Prompt:", "goodbye"))

        # get_input and confirm return default value if no user input
        self.cli.input = lambda _: ''
        self.assertTrue(self.cli.confirm("prompt"))
        self.assertEqual("goodbye", self.cli.get_input("Prompt:", "goodbye"))

        # confirm will complain and loop until receiving valid input
        def not_at_first(*_args):
            """Return 'dunno' on first call, 'y' on all subsequent calls."""
            if self.first_call:
                self.first_call = False
                return 'dunno'
            return 'y'
        self.cli.input = not_at_first
        tmp = sys.stdout
        try:
            with open(os.devnull, 'w') as devnull:
                sys.stdout = devnull
                self.assertTrue(self.cli.confirm("prompt"))
        finally:
            sys.stdout = tmp

        self.cli.getpass = lambda _: 'password'
        self.assertEqual("password", self.cli.get_password("user", "host"))

    def test_apis_with_force(self):
        """Test confirm, confirm_or_die, etc with --force option."""
        # When --force is set, CLI uses defaults and does not read user input
        self.cli.force = True
        self.cli.set_verbosity(logging.ERROR)

        self.cli.input = lambda _: 'y'
        self.assertTrue(self.cli.confirm("prompt"))
        self.cli.confirm_or_die("prompt")

        self.cli.input = lambda _: 'n'
        self.assertTrue(self.cli.confirm("prompt"))
        self.cli.confirm_or_die("prompt")

        self.cli.input = lambda _: 'hello'
        self.assertEqual("goodbye", self.cli.get_input("Prompt:", "goodbye"))

        # CLI doesn't provide a default password if --force
        self.cli.getpass = lambda _: 'password'
        self.assertRaises(InvalidInputError,
                          self.cli.get_password, "user", "host")

    def test_fill_usage(self):
        """Test fill_usage() API."""
        self.maxDiff = None     # show full diffs in case of failure
        usage = ["PACKAGE -p KEY1=VALUE1 [KEY2=VALUE2 ...] [-o OUTPUT]",
                 "PACKAGE -c CONFIG_FILE [-o OUTPUT]",
                 "PACKAGE [-o OUTPUT]"]

        self.set_terminal_width(100)
        self.assertMultiLineEqual(
            self.cli.fill_usage("edit-properties", usage), """
  cot edit-properties --help
  cot <opts> edit-properties PACKAGE -p KEY1=VALUE1 [KEY2=VALUE2 ...] \
[-o OUTPUT]
  cot <opts> edit-properties PACKAGE -c CONFIG_FILE [-o OUTPUT]
  cot <opts> edit-properties PACKAGE [-o OUTPUT]""")

        self.set_terminal_width(80)
        self.assertMultiLineEqual(
            self.cli.fill_usage("edit-properties", usage), """
  cot edit-properties --help
  cot <opts> edit-properties PACKAGE -p KEY1=VALUE1 [KEY2=VALUE2 ...]
                             [-o OUTPUT]
  cot <opts> edit-properties PACKAGE -c CONFIG_FILE [-o OUTPUT]
  cot <opts> edit-properties PACKAGE [-o OUTPUT]""")

        self.set_terminal_width(60)
        self.assertMultiLineEqual(
            self.cli.fill_usage("edit-properties", usage), """
  cot edit-properties --help
  cot <opts> edit-properties PACKAGE -p KEY1=VALUE1
                             [KEY2=VALUE2 ...] [-o OUTPUT]
  cot <opts> edit-properties PACKAGE -c CONFIG_FILE
                             [-o OUTPUT]
  cot <opts> edit-properties PACKAGE [-o OUTPUT]""")

        self.set_terminal_width(40)
        self.assertMultiLineEqual(
            self.cli.fill_usage("edit-properties", usage), """
  cot edit-properties --help
  cot <opts> edit-properties PACKAGE
      -p KEY1=VALUE1 [KEY2=VALUE2 ...]
      [-o OUTPUT]
  cot <opts> edit-properties PACKAGE
      -c CONFIG_FILE [-o OUTPUT]
  cot <opts> edit-properties PACKAGE
                             [-o OUTPUT]""")

    def test_fill_examples(self):
        """Test fill_examples() API."""
        self.maxDiff = None
        examples = [
            ("Deploy to vSphere/ESXi server 192.0.2.100 with credentials"
             " admin/admin, creating a VM named 'test' from foo.ova.",
             'cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin -n test'),
            ("Deploy to vSphere/ESXi server 192.0.2.100, with username"
             " admin (prompting the user to input a password at runtime),"
             " creating a VM based on profile '1CPU-2.5GB' in foo.ova.",
             'cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB'),
        ]

        self.set_terminal_width(100)
        self.assertMultiLineEqual("""\
Examples:
  Deploy to vSphere/ESXi server 192.0.2.100 with credentials admin/admin, \
creating a VM named
  'test' from foo.ova.

    cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin -n test

  Deploy to vSphere/ESXi server 192.0.2.100, with username admin (prompting \
the user to input a
  password at runtime), creating a VM based on profile '1CPU-2.5GB' in \
foo.ova.

    cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB""",
                                  self.cli.fill_examples(examples))

        self.set_terminal_width(80)
        self.assertMultiLineEqual("""\
Examples:
  Deploy to vSphere/ESXi server 192.0.2.100 with credentials admin/admin,
  creating a VM named 'test' from foo.ova.

    cot deploy foo.ova esxi 192.0.2.100 -u admin -p admin -n test

  Deploy to vSphere/ESXi server 192.0.2.100, with username admin (prompting \
the
  user to input a password at runtime), creating a VM based on profile
  '1CPU-2.5GB' in foo.ova.

    cot deploy foo.ova esxi 192.0.2.100 -u admin -c 1CPU-2.5GB""",
                                  self.cli.fill_examples(examples))

        self.set_terminal_width(60)
        self.assertMultiLineEqual("""\
Examples:
  Deploy to vSphere/ESXi server 192.0.2.100 with
  credentials admin/admin, creating a VM named 'test' from
  foo.ova.

    cot deploy foo.ova esxi 192.0.2.100 -u admin \\
        -p admin -n test

  Deploy to vSphere/ESXi server 192.0.2.100, with username
  admin (prompting the user to input a password at
  runtime), creating a VM based on profile '1CPU-2.5GB' in
  foo.ova.

    cot deploy foo.ova esxi 192.0.2.100 -u admin \\
        -c 1CPU-2.5GB""", self.cli.fill_examples(examples),)

        self.set_terminal_width(40)
        self.assertMultiLineEqual("""\
Examples:
  Deploy to vSphere/ESXi server
  192.0.2.100 with credentials
  admin/admin, creating a VM named
  'test' from foo.ova.

    cot deploy foo.ova esxi \\
        192.0.2.100 -u admin \\
        -p admin -n test

  Deploy to vSphere/ESXi server
  192.0.2.100, with username admin
  (prompting the user to input a
  password at runtime), creating a VM
  based on profile '1CPU-2.5GB' in
  foo.ova.

    cot deploy foo.ova esxi \\
        192.0.2.100 -u admin \\
        -c 1CPU-2.5GB""",
                                  self.cli.fill_examples(examples))


class TestCLIGeneral(TestCOTCLI):
    """CLI Test cases for top-level "cot" command."""

    def test_help(self):
        """Verify help menu for cot."""
        o1 = self.call_cot(['-h'])
        o2 = self.call_cot(['--help'])
        self.assertMultiLineEqual(o1, o2)
        if sys.hexversion < 0x03020000:
            args_str = """
  -h, --help        show this help message and exit
  -V, --version     show program's version number and exit
  -f, --force       Perform requested actions without prompting for
                    confirmation
  -q, --quiet       Quiet output and logging (warnings and errors only)
  -v, --verbose     Verbose output and logging
  -d, -vv, --debug  Debug (most verbose) output and logging
"""
            # No command aliases before Python 3.2
            command_str = """
    add-disk        Add a disk image to an OVF package and map it as a disk in
                    the guest environment
    add-file        Add a file to an OVF package
    deploy          Create a new VM on the target hypervisor from the given
                    OVF or OVA
    edit-hardware   Edit virtual machine hardware properties of an OVF
    edit-product    Edit product info in an OVF
    edit-properties
                    Edit or create environment properties of an OVF
    help            Print help for a command
    info            Generate a description of an OVF package
    inject-config   Inject a configuration file into an OVF package
    install-helpers
                    Install/verify COT manual pages and any third-party helper
                    programs that COT may require
    remove-file     Remove a file from an OVF package
"""
        else:
            # Spacing in args_str is a bit different due to subcommand aliases
            args_str = """
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  -f, --force           Perform requested actions without prompting for
                        confirmation
  -q, --quiet           Quiet output and logging (warnings and errors only)
  -v, --verbose         Verbose output and logging
  -d, -vv, --debug      Debug (most verbose) output and logging
"""
            # Help should include subcommand aliases
            command_str = """
    add-disk (add-drive)
                        Add a disk image to an OVF package and map it as a
                        disk in the guest environment
    add-file            Add a file to an OVF package
    deploy              Create a new VM on the target hypervisor from the
                        given OVF or OVA
    edit-hardware       Edit virtual machine hardware properties of an OVF
    edit-product (set-product, set-version)
                        Edit product info in an OVF
    edit-properties (set-properties, edit-environment, set-environment)
                        Edit or create environment properties of an OVF
    help                Print help for a command
    info (describe)     Generate a description of an OVF package
    inject-config (add-bootstrap)
                        Inject a configuration file into an OVF package
    install-helpers     Install/verify COT manual pages and any third-party
                        helper programs that COT may require
    remove-file (delete-file)
                        Remove a file from an OVF package
"""

        self.assertMultiLineEqual(
            """
usage: 
  cot --help
  cot --version
  cot help <command>
  cot <command> --help
  cot <options> <command> <command-options>

{0}
A tool for editing Open Virtualization Format (.ovf, .ova) virtual appliances,
with a focus on virtualized network appliances such as the Cisco CSR 1000V and
Cisco IOS XRv platforms.

optional arguments:{1}
commands:
  <command>{2}
"""  # noqa - trailing whitespace above is expected
            .format(__version_long__, args_str, command_str).strip(),
            o1.strip())

    def test_version(self):
        """Verify --version command."""
        self.call_cot(['-V'])
        self.call_cot(['--version'])

    def test_incomplete_cli(self):
        """Verify command with no subcommand is not valid."""
        # No args at all
        self.call_cot([], result=2)
        # Optional args but no subcommand
        self.call_cot(['-f', '-v'], fixup_args=False, result=2)

    def test_verbosity(self):
        """Verify various verbosity options and their effect on logging."""
        self.logging_handler.flush()

        # Default verbosity is INFO
        self.call_cot(['info', self.invalid_ovf], fixup_args=False)
        self.assertNotEqual(
            [], self.logging_handler.logs(levelname='ERROR'))
        self.assertNotEqual(
            [], self.logging_handler.logs(levelname='WARNING'))
        self.assertNotEqual(
            [], self.logging_handler.logs(levelname='INFO'))
        self.assertEqual(
            [], self.logging_handler.logs(levelname='VERBOSE'))
        self.assertEqual(
            [], self.logging_handler.logs(levelname='DEBUG'))
        self.logging_handler.flush()

        # -v/--verbose gives VERBOSE
        for OPT in ['-v', '--verbose']:
            self.call_cot([OPT, 'info', self.invalid_ovf], fixup_args=False)
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='ERROR'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='WARNING'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='INFO'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='VERBOSE'))
            self.assertEqual(
                [], self.logging_handler.logs(levelname='DEBUG'))
            self.logging_handler.flush()

        # -vv/-d/--debug gives DEBUG
        for OPT in ['-vv', '-d', '--debug']:
            self.call_cot([OPT, 'info', self.invalid_ovf], fixup_args=False)
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='ERROR'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='WARNING'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='INFO'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='VERBOSE'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='DEBUG'))
            self.logging_handler.flush()

        # -q/--quiet gives WARNING
        for OPT in ['-q', '--quiet']:
            self.call_cot([OPT, 'info', self.invalid_ovf], fixup_args=False)
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='ERROR'))
            self.assertNotEqual(
                [], self.logging_handler.logs(levelname='WARNING'))
            self.assertEqual(
                [], self.logging_handler.logs(levelname='INFO'))
            self.assertEqual(
                [], self.logging_handler.logs(levelname='VERBOSE'))
            self.assertEqual(
                [], self.logging_handler.logs(levelname='DEBUG'))
            self.logging_handler.flush()


class TestCLIAddDisk(TestCOTCLI):
    """CLI test cases for "cot add-disk" command."""

    def test_help(self):
        """Verify help menu for cot add-disk."""
        self.call_cot(['add-disk', "-h"])

    def test_invalid_args(self):
        """Testing various missing or incorrect parameters."""
        disk_path = self.blank_vmdk
        # No disk or VM specified
        self.call_cot(['add-disk'], result=2)
        # Disk but no VM
        self.call_cot(['add-disk', disk_path], result=2)
        # Nonexistent VM specified
        self.call_cot(['add-disk', disk_path, '/foo'], result=2)
        # Incorrect type parameter
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-t', 'dvd'],
                      result=2)
        # Incorrect controller parameter
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ata'],
                      result=2)
        # Incorrectly formatted address parameter
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "1"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', ":1"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "1600 Pennsylvania Avenue"], result=2)
        # Correctly formatted but out-of-range address parameters:
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "2:0"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'ide',
                       '-a', "0:2"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'scsi',
                       '-a', "4:0"], result=2)
        self.call_cot(['add-disk', disk_path, self.input_ovf, '-c', 'scsi',
                       '-a', "0:16"], result=2)

        # Missing strings
        for param in ['-f', '-t', '-c', '-a', '-s', '-d', '-n']:
            self.call_cot(['add-disk', disk_path, self.input_ovf, param],
                          result=2)
        # Package file exists but filename shows it is not an OVF/OVA
        self.call_cot(['add-disk', disk_path, disk_path], result=2)
        # Package file claims to be an OVF/OVA, but is not actually XML.
        fake_file = os.path.join(self.temp_dir, "foo.ovf")
        with open(fake_file, 'w') as f:
            f.write("< hello world!")
        self.call_cot(['add-disk', disk_path, fake_file], result=2)
        # Package file claims to be an OVF/OVA, but is some other XML.
        with open(fake_file, 'w') as f:
            f.write("<xml />")
        self.call_cot(['add-disk', disk_path, fake_file], result=2)

    def test_nonexistent_file(self):
        """Pass in a file or VM that doesn't exist."""
        # Disk exists but VM does not
        self.call_cot(['add-disk', self.blank_vmdk, '/foo/bar.ovf'], result=2)
        # VM exists but disk does not
        self.call_cot(['add-disk', '/foo/bar.vmdk', self.input_ovf],
                      result=2)

    def test_unknown_filetype(self):
        """Pass in a file that is not obviously a CDROM or hard disk."""
        # Unknown extension
        mystery_file = os.path.join(self.temp_dir, "foo.bar")
        open(mystery_file, 'a').close()
        self.call_cot(['add-disk', mystery_file, self.input_ovf,
                       '-o', self.temp_file],
                      result=2)
        # No extension
        mystery_file = os.path.join(self.temp_dir, "foo")
        open(mystery_file, 'a').close()
        self.call_cot(['add-disk', mystery_file, self.input_ovf,
                       '-o', self.temp_file],
                      result=2)


class TestCLIAddFile(TestCOTCLI):
    """CLI test cases for "cot add-file" command."""

    def test_help(self):
        """Verify help menu for cot add-file."""
        self.call_cot(['add-file', "-h"])

    def test_invalid_args(self):
        """Test various missing or incorrect parameters."""
        # No file or VM specified
        self.call_cot(['add-file'], result=2)
        # File but no VM
        self.call_cot(['add-file', self.blank_vmdk], result=2)
        # Nonexistent VM specified
        self.call_cot(['add-file', self.blank_vmdk, '/foo'], result=2)
        # Missing strings
        for param in ['-f']:
            self.call_cot(['add-file', self.blank_vmdk, self.input_ovf, param],
                          result=2)

    def test_nonexistent_file(self):
        """Pass in a file or VM that doesn't exist."""
        # Disk exists but VM does not
        self.call_cot(['add-file', self.blank_vmdk, '/foo/bar.ovf'], result=2)
        # VM exists but disk does not
        self.call_cot(['add-file', '/foo/bar.vmdk', self.input_ovf],
                      result=2)


class TestCLIEditHardware(TestCOTCLI):
    """CLI test cases for "cot edit-hardware" command."""

    def test_help(self):
        """Verify help menu for cot edit-hardware."""
        self.call_cot(['edit-hardware', "-h"])

    def test_invalid_args(self):
        """Test various missing or incorrect parameters."""
        # No VM specified
        self.call_cot(['edit-hardware'], result=2)
        # Nonexistent VM specified
        self.call_cot(['edit-hardware', '/foo', '-o', self.temp_file],
                      result=2)

        base_args = ['edit-hardware', self.input_ovf,
                     '-o', self.temp_file]
        # Arguments missing values
        for arg in ['-p', '--profile', '-c', '--cpus',
                    '-m', '--memory', '-n', '--nics',
                    '-N', '--nic-networks',
                    '--nic-types', '--nic-count',
                    '-M', '--mac-addresses-list',
                    '-s', '--serial-ports', '-S', '--serial-connectivity',
                    '--scsi-subtype', '--ide-subtype',
                    '-v', '--virtual-system-type']:
            self.call_cot(base_args + [arg], result=2)
        # Invalid profile string
        self.call_cot(base_args + ['-p', '2 CPUs, 2 GB RAM'], result=2)
        # Invalid CPUs value
        for arg in ['-c', '--cpus']:
            self.call_cot(base_args + [arg, '0'], result=2)
        # Invalid memory value
        self.call_cot(base_args + ['-m', '512k'], result=2)
        self.call_cot(base_args + ['--memory', '0'], result=2)
        # Invalid MAC address
        self.call_cot(base_args + ['-M', 'fe:fi:f0:ff:ff:ff'], result=2)
        # Invalid NIC type
        self.call_cot(base_args + ['--nic_type', 'GLENN'], result=2)

    def test_args_append(self):
        """Test for https://github.com/glennmatthews/cot/issues/58."""
        # Multiple parameters for each arg:
        self.call_cot(['edit-hardware', self.input_ovf, '-o', self.temp_file,
                       '-v', 'vmx-08', 'vmx-09',
                       '--nic-types', 'e1000', 'virtio',
                       '--nic-names', 'mgmt', 'eth{1}',
                       '-N', 'VM Network', 'Eth{1}',
                       '--network-descriptions', 'VM Network', 'Ethernet {1}',
                       '-M', '00:00:00:00:00:00', '00:00:00:00:00:01',
                       '-S', 'telnet://localhost:1', 'telnet://localhost:2',
                       '--scsi-subtypes', 'lsilogic', 'virtio',
                       '--ide-subtypes', 'PIIX4', 'virtio'])
        self.assertLogged(**self.creating_network_warning('Eth1'))
        self.assertLogged(**self.creating_network_warning('Eth2'))
        self.check_diff("""
       <ovf:Description>VM Network</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="Eth1">
+      <ovf:Description>Ethernet 1</ovf:Description>
+    </ovf:Network>
+    <ovf:Network ovf:name="Eth2">
+      <ovf:Description>Ethernet 2</ovf:Description>
     </ovf:Network>
...
         <vssd:VirtualSystemIdentifier>test</vssd:VirtualSystemIdentifier>
-        <vssd:VirtualSystemType>vmx-07 vmx-08</vssd:VirtualSystemType>
+        <vssd:VirtualSystemType>vmx-08 vmx-09</vssd:VirtualSystemType>
       </ovf:System>
...
         <rasd:InstanceID>3</rasd:InstanceID>
-        <rasd:ResourceSubType>lsilogic</rasd:ResourceSubType>
+        <rasd:ResourceSubType>lsilogic virtio</rasd:ResourceSubType>
         <rasd:ResourceType>6</rasd:ResourceType>
...
         <rasd:InstanceID>4</rasd:InstanceID>
+        <rasd:ResourceSubType>PIIX4 virtio</rasd:ResourceSubType>
         <rasd:ResourceType>5</rasd:ResourceType>
...
         <rasd:InstanceID>5</rasd:InstanceID>
+        <rasd:ResourceSubType>PIIX4 virtio</rasd:ResourceSubType>
         <rasd:ResourceType>5</rasd:ResourceType>
...
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:1</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
       <ovf:Item ovf:required="false">
+        <rasd:Address>telnet://localhost:2</rasd:Address>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
...
       <ovf:Item>
+        <rasd:Address>00:00:00:00:00:00</rasd:Address>
         <rasd:AddressOnParent>11</rasd:AddressOnParent>
...
         <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet1</rasd:ElementName>
+        <rasd:Description>E1000/virtio ethernet adapter on "VM Network"\
</rasd:Description>
+        <rasd:ElementName>mgmt</rasd:ElementName>
         <rasd:InstanceID>11</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000 virtio</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>00:00:00:00:00:01</rasd:Address>
         <rasd:AddressOnParent>12</rasd:AddressOnParent>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet2</rasd:ElementName>
+        <rasd:Connection>Eth1</rasd:Connection>
+        <rasd:Description>E1000/virtio ethernet adapter on "Eth1"\
</rasd:Description>
+        <rasd:ElementName>eth1</rasd:ElementName>
         <rasd:InstanceID>12</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000 virtio</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
...
       <ovf:Item ovf:configuration="4CPU-4GB-3NIC">
+        <rasd:Address>00:00:00:00:00:01</rasd:Address>
         <rasd:AddressOnParent>13</rasd:AddressOnParent>
         <rasd:AutomaticAllocation>true</rasd:AutomaticAllocation>
-        <rasd:Connection>VM Network</rasd:Connection>
-        <rasd:Description>VMXNET3 ethernet adapter on "VM Network"\
</rasd:Description>
-        <rasd:ElementName>GigabitEthernet3</rasd:ElementName>
+        <rasd:Connection>Eth2</rasd:Connection>
+        <rasd:Description>E1000/virtio ethernet adapter on "Eth2"\
</rasd:Description>
+        <rasd:ElementName>eth2</rasd:ElementName>
         <rasd:InstanceID>13</rasd:InstanceID>
-        <rasd:ResourceSubType>VMXNET3</rasd:ResourceSubType>
+        <rasd:ResourceSubType>E1000 virtio</rasd:ResourceSubType>
         <rasd:ResourceType>10</rasd:ResourceType>
""")

        temp_file_2 = os.path.join(self.temp_dir, "out2.ovf")
        # Multiple instances of each arg:
        self.call_cot(['edit-hardware', self.input_ovf, '-o', temp_file_2,
                       '-v', 'vmx-08', '-v', 'vmx-09',
                       '--nic-types', 'e1000', '--nic-types', 'virtio',
                       '--nic-names', 'mgmt', '--nic-names', 'eth{1}',
                       '-N', 'VM Network', '-N', 'Eth{1}',
                       '--network-descriptions', 'VM Network',
                       '--network-descriptions', 'Ethernet {1}',
                       '-M', '00:00:00:00:00:00', '-M', '00:00:00:00:00:01',
                       '-S', 'telnet://localhost:1',
                       '-S', 'telnet://localhost:2',
                       '--scsi-subtypes', 'lsilogic',
                       '--scsi-subtypes', 'virtio',
                       '--ide-subtypes', 'PIIX4', '--ide-subtypes', 'virtio'])
        self.assertLogged(**self.creating_network_warning('Eth1'))
        self.assertLogged(**self.creating_network_warning('Eth2'))

        # Both inputs should create the same output OVF.
        self.check_diff("", file1=self.temp_file, file2=temp_file_2)


class TestCLIEditProduct(TestCOTCLI):
    """CLI test cases for "cot edit-product" command."""

    def test_help(self):
        """Verify help menu for cot edit-product."""
        self.call_cot(['edit-product', "-h"])

    def test_invalid_args(self):
        """Test various missing or incorrect parameters."""
        # No VM specified
        self.call_cot(['edit-product'], result=2)
        # Nonexistent VM specified
        self.call_cot(['edit-product', '/foo'], result=2)
        # Missing strings
        self.call_cot(['edit-product', self.input_ovf, '-v'], result=2)
        self.call_cot(['edit-product', self.input_ovf, '-V'], result=2)
        self.call_cot(['edit-product', self.input_ovf, '-V', '-v'], result=2)


class TestCLIEditProperties(TestCOTCLI):
    """CLI test cases for "cot edit-properties" command."""

    def test_help(self):
        """Verify help menu for cot edit-properties."""
        self.call_cot(['edit-properties', '-h'])

    def test_invalid_args(self):
        """Test various missing or incorrect parameters."""
        # No VM specified
        self.call_cot(['edit-properties'], result=2)
        # Nonexistent VM specified
        self.call_cot(['edit-properties', '/foo'], result=2)
        # Missing strings
        self.call_cot(['edit-properties', self.input_ovf, '--config-file'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--properties'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--output'],
                      result=2)
        # Nonexistent files
        self.call_cot(['edit-properties', self.input_ovf, '--config-file',
                       '/foo'], result=2)
        # Bad input format
        self.call_cot(['edit-properties', self.input_ovf, '--properties', '='],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--properties',
                       '=foo'], result=2)
        self.call_cot(['edit-properties', self.input_ovf, '--properties', '+'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '-p', '+string'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf, '-p', '=foo+string'],
                      result=2)
        self.call_cot(['edit-properties', self.input_ovf,
                       '--user-configurable', 'foobar'], result=2)

    def test_set_property_valid(self):
        """Variant property setting syntax, exercising CLI nargs/append."""
        for args in (['-p', 'login-username=admin',   # Individual
                      '-p', 'login-password=cisco123',
                      '-p', 'enable-ssh-server=1'],
                     ['-p', 'login-username=admin',   # All for one
                            'login-password=cisco123',
                            'enable-ssh-server=1'],
                     ['-p', 'login-username=admin',   # Mixed!
                      '-p', 'login-password=cisco123',
                            'enable-ssh-server=1'],
                     ['-p', 'login-username=admin',   # Differently mixed!
                            'login-password=cisco123',
                      '-p', 'enable-ssh-server=1']):
            self.call_cot(['edit-properties', self.input_ovf,
                           '-o', self.temp_file] + args)
            self.check_diff("""
       <ovf:Category>1. Bootstrap Properties</ovf:Category>
-      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="">
+      <ovf:Property ovf:key="login-username" ovf:qualifiers="MaxLen(64)" \
ovf:type="string" ovf:userConfigurable="true" ovf:value="admin">
         <ovf:Label>Login Username</ovf:Label>
...
       </ovf:Property>
-      <ovf:Property ovf:key="login-password" ovf:password="true" \
ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" \
ovf:value="">
+      <ovf:Property ovf:key="login-password" ovf:password="true" \
ovf:qualifiers="MaxLen(25)" ovf:type="string" ovf:userConfigurable="true" \
ovf:value="cisco123">
         <ovf:Label>Login Password</ovf:Label>
...
       <ovf:Category>2. Features</ovf:Category>
-      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="false">
+      <ovf:Property ovf:key="enable-ssh-server" ovf:type="boolean" \
ovf:userConfigurable="true" ovf:value="true">
         <ovf:Label>Enable SSH Login</ovf:Label>
""")


class TestCLIHelp(TestCOTCLI):
    """CLI test cases for "cot help" command."""

    def test_help_positive(self):
        """Positive tests for cot help."""
        self.call_cot(['help'])
        self.call_cot(['help', 'add-disk'])
        self.call_cot(['help', 'add-file'])
        self.call_cot(['help', 'deploy'])
        self.call_cot(['help', 'edit-hardware'])
        self.call_cot(['help', 'edit-product'])
        self.call_cot(['help', 'edit-properties'])
        self.call_cot(['help', 'help'])
        self.call_cot(['help', 'info'])
        self.call_cot(['help', 'inject-config'])
        self.call_cot(['help', 'remove-file'])

    def test_help_negative(self):
        """Negative tests for cot help."""
        self.call_cot(['help', 'frobozz'], result=2)
        self.call_cot(['help', 'add-disk', 'add-file'], result=2)


class TestCLIInfo(TestCOTCLI):
    """CLI test cases for "cot info" command."""

    def test_help(self):
        """Verify help menu for cot info."""
        self.call_cot(['info', "-h"])


class TestCLIInjectConfig(TestCOTCLI):
    """CLI test cases for "cot inject-config" command."""

    def test_help(self):
        """Verify help menu for cot inject-config."""
        self.call_cot(['inject-config', '-h'])

    def test_invalid_args(self):
        """Test various missing or incorrect parameters."""
        # No VM specified
        self.call_cot(['inject-config'], result=2)
        # Nonexistent VM specified
        self.call_cot(['inject-config', '/foo'], result=2)
        # Missing strings
        self.call_cot(['inject-config', self.input_ovf, '-c'], result=2)
        self.call_cot(['inject-config', self.input_ovf, '-s'], result=2)
        self.call_cot(['inject-config', self.input_ovf, '-e'], result=2)
        # Nonexistent config files
        self.call_cot(['inject-config', self.input_ovf,
                       '-c', '/foo'], result=2)
        self.call_cot(['inject-config', self.input_ovf,
                       '-s', '/foo'], result=2)
        self.call_cot(['inject-config', self.input_ovf,
                       '-e', '/foo'], result=2)


class TestCLIDeploy(TestCOTCLI):
    """CLI test cases for "cot deploy" command."""

    def test_help(self):
        """Verify help menu for cot deploy."""
        self.call_cot(['deploy', '-h'])

    def test_invalid_args(self):
        """Negative testing for cot deploy CLI."""
        # No VM specified
        self.call_cot(['deploy'], result=2)
        # VM does not exist
        self.call_cot(['deploy', '/foo'], result=2)
        # Hypervisor not specified
        self.call_cot(['deploy', self.input_ovf], result=2)
        # Invalid hypervisor
        self.call_cot(['deploy', self.input_ovf, 'MyHypervisor'], result=2)


class TestCLIDeployESXi(TestCOTCLI):
    """CLI test cases for 'cot deploy PACKAGE esxi' command."""

    def test_help(self):
        """Verify help menu for cot deploy ... esxi."""
        self.call_cot(['deploy', self.input_ovf, '-h'])

    def test_invalid_args_no_locator(self):
        """Negative test: no locator specified."""
        self.call_cot(['deploy', self.input_ovf, 'esxi'],
                      result=2)

    def test_invalid_args_no_password_noninteractive(self):
        """No password specified - required if running noninteractively."""
        self.call_cot(['deploy', self.minimal_ovf, 'esxi', 'localhost'],
                      result=2)

    def test_invalid_args_missing_strings(self):
        """Negative test: Missing strings."""
        for param in ['-c', '-n', '-N', '-u', '-p', '-d', '-o']:
            self.call_cot(['deploy', self.input_ovf, 'esxi', 'localhost',
                           '-p', 'password', param],
                          result=2)

    def test_invalid_args_invalid_configuration(self):
        """Negative test: Invalid configuration profile."""
        self.call_cot(['deploy', self.input_ovf, 'esxi', 'localhost',
                       '-p', 'password', '-c', 'nonexistent'],
                      result=2)

    def test_invalid_args_too_many_serial(self):
        """Negative test: ESXi maxes at 4 serial ports."""
        self.call_cot(['deploy', self.input_ovf, 'esxi', 'localhost',
                       '-S', 'tcp::2001', '-S', 'tcp::2002', '-S', 'tcp::2003',
                       '-S', 'tcp::2004', '-S', 'tcp::2005'],
                      result=2)


class TestCLIInstallHelpers(TestCOTCLI):
    """CLI test cases for 'COT install-helpers' subcommand."""

    def test_help(self):
        """Verify help menu for cot install-helpers."""
        self.call_cot(['install-helpers', '-h'])

    def test_invalid_args(self):
        """Invalid combinations of arguments."""
        # Mutually exclusive
        self.call_cot(['install-helpers', '--ignore-errors', '--verify-only'],
                      result=2)


class TestCLIRemoveFile(TestCOTCLI):
    """CLI test cases for 'cot remove-file' subcommand."""

    def test_help(self):
        """Verify help menu for cot remove-file."""
        self.call_cot(['remove-file', '-h'])

    def test_invalid_args(self):
        """Invalid combinations of arguments."""
        # input.vmdk is file1, file2 is input.iso
        self.call_cot(['remove-file', self.input_ovf, '-o', self.temp_file,
                       '--file-path', 'input.vmdk', '--file-id', 'file2'],
                      result=2)
        # file1 is not foo.bar
        self.call_cot(['remove-file', self.input_ovf, '-o', self.temp_file,
                       '--file-id', 'file1', '--file-path', 'foo.bar'],
                      result=2)
        # input.vmdk is not "frobozz"
        self.call_cot(['remove-file', self.input_ovf, '-o', self.temp_file,
                       '--file-path', 'input.vmdk', '--file-id', 'frobozz'],
                      result=2)
