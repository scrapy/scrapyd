# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# -- Project information -----------------------------------------------------

project = "Scrapyd"
copyright = "2013-2023, Scrapy group"
author = "Scrapy group"

# The short X.Y version
version = "1.6.0"
# The full version, including alpha/beta/rc tags
release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "sphinxcontrib.zopeext.autointerface",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []


# -- Extension configuration -------------------------------------------------

autodoc_default_options = {
    "members": None,
    "member-order": "bysource",
}
autodoc_typehints = "description"
autodoc_type_aliases = {}

extlinks = {
    "issue": ("https://github.com/open-contracting/pelican-frontend/issues/%s", "#%s"),
    "commit": ("https://github.com/open-contracting/pelican-frontend/commit/%s", "%s"),
}
