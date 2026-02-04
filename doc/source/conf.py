# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../../src/"))

autodoc_mock_imports = [
    'building_stock_model',
    'tests.conftest',
    'server.Launch',
    'mesa_geo',
    'geopandas',
    'dotenv',
    'plotly',
    'dill',
    'statsmodels',
    'SALib',
    ]

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'AHOIS-pro'
copyright = '2025, Ivan Digel, Sascha Holzhauer'
author = 'Ivan Digel, Sascha Holzhauer'
release = '0.5'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    "sphinx.ext.autodoc",
    "numpydoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosectionlabel",
    "sphinxcontrib.excel_table",
    "sphinx_copybutton",
    "docxbuilder",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

source_suffix = ".rst"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_css_files = [
    "custom.css",
]

html_extra_path = [
    "_res",
]

# Own additions
numpydoc_show_class_members = (
    False 
)

intersphinx_mapping = {
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
}

add_module_names = False

todo_include_todos = True

# Sort members by the order in the source files instead of alphabetically
autodoc_member_order = "bysource"

# Show both the class-level docstring and the constructor docstring
autoclass_content = "both"

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# prefix each section label with the name of the document it is in, followed by a colon
autosectionlabel_prefix_document = True

docx_documents = [
    (
        "index",
        "docxbuilder.docx",
        {
            "title": "AHOIS pro",
            "creator": "AHOIS pro Team",
            "subject": '"Documentation for Users, Stakeholders and Developers"',
        },
        True,
    ),
]
# docx_style = 'path/to/custom_style.docx'
docx_pagebreak_before_section = 1
contact = "Ivan Digel (ivan.digel@uni-kassel.de)"

rst_prolog = f"""
.. |contact| replace:: {contact}
"""
