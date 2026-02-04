"""
Packaging and distribution script for the AHOIS project.

This file uses "setuptools" to manage the packaging, installation, and
distribution of the "AHOIS" agent-based model. It defines essential 
metadata such as the project's name, version, and author.

The script also specifies:
- Core dependencies required for the model to run.
- Optional dependencies for development (e.g., testing) and for building
  the documentation.
- Custom commands for handling internationalisation 
  and localisation with the `Babel` library.
  
:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
from setuptools import setup, find_packages
from distutils.core import setup
from babel.messages import frontend as babel

requires = ["numpy", "pandas"]

extras_require = {
    "dev": [
        "pytest >= 4.6",
        "pytest-cov",
        "Babel",
    ],
    "docs": [
        "sphinx",
        "docxbuilder",
        "numpydoc",
        "sphinx_rtd_theme",
    ],
}

setup(
    name="AHOI",
    version="0.1",
    description="Agent-based modeling (ABM) of heat system decision making",
    long_description="NN",
    author="Ivan Digel, Sascha Holzhauer",
    author_email="ivan.digel@uni-kassel.de",
    url="https://www.uni-kassel.de/go/ines",
    packages=find_packages(),
    package_data={},
    include_package_data=True,
    install_requires=requires,
    extras_require=extras_require,
    keywords="agent based modeling model ABM simulation multi-agent",
    license="GPL-3.0-or-later",
    zip_safe=False,
    classifiers=[
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Life",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Natural Language :: English",
    ],
    entry_points="""
        [console_scripts]
        mesa=mesa.main:cli
    """,
    python_requires=">=3.8",
    cmdclass={
        "compile_catalog": babel.compile_catalog,
        "extract_messages": babel.extract_messages,
        "init_catalog": babel.init_catalog,
        "update_catalog": babel.update_catalog,
    },
)
