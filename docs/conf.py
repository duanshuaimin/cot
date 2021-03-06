# -*- coding: utf-8 -*-
#
# common-ovf-tool documentation build configuration file, created by
# sphinx-quickstart on Tue Feb 10 16:27:53 2015.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

"""COT documentation build configuration file."""

import logging
import os
import re
import shutil
import sys

logger = logging.getLogger(__name__)

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))


def regenerate_usage_contents(force=False):
    """Get CLI usage strings for all submodules and write them to file."""
    COT_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    logger.info("COT path: "+COT_path)
    sys.path.insert(0, COT_path)
    from COT.cli import CLI
    # Don't use our actual terminal width as it may vary.
    # Instead, use 79 chars minus the 8-character indent used in man pages.
    cli = CLI(terminal_width=71)

    for subcommand in [
            "cot",
            "add-disk",
            "add-file",
            "deploy",
            "deploy-esxi",
            "edit-hardware",
            "edit-product",
            "edit-properties",
            "info",
            "inject-config",
            "install-helpers",
            "remove-file",
    ]:
        dirpath = os.path.join(os.path.dirname(__file__),
                               "_autogenerated", subcommand)
        if os.path.exists(dirpath):
            if not force:
                logger.warning("Directory {0} already exists, skipping '{1}'. "
                               .format(dirpath, subcommand))
                continue
            shutil.rmtree(dirpath)
        os.makedirs(dirpath)

        if subcommand == "cot":
            logger.debug("Getting top-level help for 'cot'...")
            help = cli.parser.format_help()
        else:
            logger.debug("Getting help for 'cot {0}'...".format(subcommand))
            help = cli.subparser_lookup[subcommand].format_help()
        assert help, "help is empty!"

        logger.debug("Converting help string to reStructuredText...")
        help_text_to_rst(help, dirpath)

    logger.info("Done updating help rst files")


def help_text_to_rst(help, dirpath):
    """Convert CLI usage string from plaintext to RST and write to files."""
    synopsis_lines = []
    description_lines = []
    options_lines = []
    notes_lines = []
    examples_lines = []
    in_synopsis = False
    in_description = False
    in_options = False
    in_notes = False
    in_examples = False

    for line in help.splitlines():
        if re.match("^usage:", line):
            synopsis_lines.append("Synopsis")
            synopsis_lines.append("--------")
            synopsis_lines.append("::")
            synopsis_lines.append("")
            in_synopsis = True
            continue
        elif in_synopsis and not re.match("^  ", line):
            description_lines.append("Description")
            description_lines.append("-----------")
            in_synopsis = False
            in_description = True
        elif in_description and re.match("^Copyright", line):
            # Special case for top-level 'cot' CLI
            description_lines.append("")
            continue
        elif in_description and re.match("^\S.*:$", line):
            options_lines.append("Options")
            options_lines.append("-------")
            options_lines.append("")
            if not re.match("(optional|positional) arguments", line):
                # Options subsection - strip trailing ':'
                section = line.rstrip()[:-1].capitalize()
                options_lines.append(section)
                options_lines.append("*" * len(section))
            in_description = False
            in_options = True
            continue
        elif in_options and re.match("^Notes", line):
            # Entering the (optional) notes epilog
            notes_lines.append("Notes")
            notes_lines.append("-----")
            notes_lines.append("")
            in_options = False
            in_notes = True
            continue
        elif (in_options or in_notes) and re.match("^Example", line):
            # Entering the (optional) examples epilog
            examples_lines.append("Examples")
            examples_lines.append("--------")
            examples_lines.append("")
            in_options = False
            in_notes = False
            in_examples = True
            continue
        elif in_options and re.match("^\S", line):
            if not re.match("(optional|positional) arguments", line):
                # Options subsection - strip trailing ':'
                section = line.rstrip()[:-1].capitalize()
                options_lines.append(section)
                options_lines.append("*" * len(section))
            continue
        elif in_options and re.match("^  <", line):
            # metavar for subparser, such as <command> or <hypervisor>
            continue
        elif in_options and re.match("^   ? ?\S", line):
            # New argument
            # Do we have any trailing text?
            match = re.match("^   ? ?(.*\S)  +(\S.*)", line)
            if match:
                line = match.group(1).strip()
                desc_line = "  " + (match.group(2).strip())
            else:
                line = line.strip()
                desc_line = None

            # RST is picky about what an option's values look like,
            # so we have to do some cleanup of the argparse presentation:

            # RST dislikes multi-char args with one dash like '-ds' or '-vv'.
            # All of the ones COT has are synonyms for 'proper' args, so we'll
            # just omit these synonyms from the docs.
            line = re.sub(r" -[a-z][a-z]+( \S+)?,?", "", line)

            # --type {e1000,virtio}   ---->   --type <e1000,virtio>
            line = re.sub(r"(-+\S+) {([^}]+)}", r"\1 <\2>", line)

            # -u [USER_CONFIGURABLE] ----> -u <USER_CONFIGURABLE>
            line = re.sub(r"(-+\S+) \[([^,]+)\]", r"\1 <\2>", line)

            # --names NAME1 [NAME2 ...] ---->  --names <NAME1...>
            line = re.sub(r"(-+\S+) (\S+) \[\S+ \.\.\.\]",
                          r"\1 <\2...>", line)

            # foobar (foo, bar) ----> foobar, foo, bar
            line = re.sub(r"(\S+) \((.*)\)", r"\1, \2", line)

            if desc_line:
                options_lines.append(line)
                line = desc_line
        elif in_options and re.match("^        ", line):
            # Description of an option - keep it under the option_list
            line = "  " + line.strip()
        elif in_notes:
            line = line.strip()
        elif in_examples and re.match("^    ", line):
            # Beginning of an example - mark as a literal
            if not re.match("^    ", examples_lines[-1]):
                examples_lines.append("::")
                examples_lines.append("")
        elif in_examples and re.match("^  \S", line):
            # Description of an example - exit any literal block
            if re.match("^    ", examples_lines[-1]):
                examples_lines.append("")
            line = line.strip()
        else:
            pass

        if line.rstrip():
            line = line.rstrip()
        if in_synopsis:
            synopsis_lines.append(line)
        elif in_description:
            description_lines.append(line)
        elif in_options:
            options_lines.append(line)
        elif in_notes:
            notes_lines.append(line)
        elif in_examples:
            examples_lines.append(line)
        else:
            raise RuntimeError("Not sure what to do with line:\n{0}"
                               .format(line))

    output = {
        'synopsis': "\n".join(synopsis_lines),
        'description': "\n".join(description_lines),
        'options': "\n".join(options_lines),
        'notes': "\n".join(notes_lines),
        'examples': "\n".join(examples_lines)
    }

    for key, value in output.items():
        filepath = os.path.join(dirpath, "{0}.txt".format(key))
        logger.debug("Writing to {0}".format(filepath))
        with open(filepath, 'w') as f:
            f.write(value)

regenerate_usage_contents(force=True)

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.3'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.ifconfig',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
]

# -- Autodoc configuration --------------------

# Class documentation - class (default), init, or both
# autoclass_content = 'both'

# Sorting of members - alphabetical (default), groupwise, or bysource
autodoc_member_order = 'groupwise'

# Default flags for all autodoc directives.
# members, undoc-members, private-members, special-members, inherited-members,
# show-inheritance
autodoc_default_flags = ['members', 'undoc-members', 'show-inheritance']

def autodoc_skip_member(app, what, name, obj, skip, options):
    """Always document __init__ method."""
    if name == "__init__":
        return False
    return skip

# -- Intersphinx configuration ----------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('http://docs.python-requests.org/en/latest', None),
}

# -- Napoleon configuration -------------------

napoleon_use_rtype = False

# -- General configuration, continued ---------

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Common OVF Tool (COT)'
copyright = u'2013-2017, the COT project developers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
from COT._version import get_versions   # noqa

versioneer_string = get_versions()["version"]
# readthedocs patches conf.py, causing git to report the version as 'dirty',
# and hence causing versioneer to do likewise. Let's clean that up.
if re.search(".dirty$", versioneer_string):
    versioneer_string = versioneer_string[:-6]
# Get the tagged version number:
release = versioneer_string.split("+")[0]
# If the commit count is 0 we are on a tagged version and the above
# suffices. If it's greater than zero, let's append that
post0 = re.search("\+([1-9][0-9]*)", versioneer_string)
if post0:
    # We are past a tagged version by +N commits
    commit_count = post0.group(1)
    release += " (plus {0} commits)".format(commit_count)

version = release

logger.info("\n".join([project, version, release]))

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ["/test/"]

# The reST default role (used for this markup: `text`) to use for all
# documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['COT']

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'default'
# html_theme = 'nature'

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from
# docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    html_context = {
        'css_files': ['_static/theme_overrides.css']
    }
else:
    # readthedocs.org uses their theme by default, so no need to specify it
    # Make sure we add to the RTD stylesheets, not replace them entirely:
    html_context = {
        'css_files': [
            'https://media.readthedocs.org/css/sphinx_rtd_theme.css',
            'https://media.readthedocs.org/css/readthedocs-doc-embed.css',
            '_static/theme_overrides.css',
        ],
    }

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "COT documentation"

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "Common OVF Tool (COT)"

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
# html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'common-ovf-tooldoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    # 'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'common-ovf-tool.tex', u'common-ovf-tool Documentation',
     u'the COT project developers', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('usage_general', 'cot',
     u'Common OVF Tool',
     [u'Glenn F. Matthews'], 1),
    ('usage_add_disk', 'cot-add-disk',
     u'Add or replace a disk image in an OVF or OVA',
     [u'Glenn F. Matthews'], 1),
    ('usage_add_file', 'cot-add-file',
     u'Add or replace a file in an OVF or OVA',
     [u'Glenn F. Matthews'], 1),
    ('usage_deploy', 'cot-deploy',
     u'Deploy an OVF or OVA to create a virtual machine',
     ['Kevin A. Keim', 'Glenn F. Matthews'], 1),
    ('usage_deploy_esxi', 'cot-deploy-esxi',
     u'Deploy an OVF or OVA to ESXi, VMware vSphere, or VMware vCenter',
     ['Kevin A. Keim', 'Glenn F. Matthews'], 1),
    ('usage_edit_hardware', 'cot-edit-hardware',
     u'Edit hardware properties and configuration profiles of an OVF or OVA',
     [u'Glenn F. Matthews'], 1),
    ('usage_edit_product', 'cot-edit-product',
     u'Edit OVF/OVA product information such as version strings',
     [u'Glenn F. Matthews'], 1),
    ('usage_edit_properties', 'cot-edit-properties',
     u'Configure environment properties for an OVF or OVA',
     [u'Glenn F. Matthews'], 1),
    ('usage_install_helpers', 'cot-install-helpers',
     u'Install helper programs used by COT',
     [u'Glenn F. Matthews'], 1),
    ('usage_info', 'cot-info',
     u'Summarize the contents of OVF(s) and/or OVA(s)',
     [u'Glenn F. Matthews'], 1),
    ('usage_inject_config', 'cot-inject-config',
     u'Add bootstrap configuration to an OVF or OVA',
     [u'Glenn F. Matthews'], 1),
    ('usage_remove_file', 'cot-remove-file',
     u'Remove file from an OVF or OVA',
     [u'Glenn F. Matthews'], 1),
]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'common-ovf-tool', u'common-ovf-tool Documentation',
     u'the COT project developers', 'common-ovf-tool',
     'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
# texinfo_appendices = []

# If false, no module index is generated.
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
# texinfo_no_detailmenu = False

def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)
