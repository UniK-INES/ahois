"""
Handles localisation for the project.

This module sets up the translation framework using Python's built-in `gettext`
library. It locates the translation files, configures the desired language based
on the global settings (`settings.eval.language`), and provides a translation
function, conventionally named `_`. This function can be imported and used
throughout the project to mark strings for translation.

:Authors:

 - Sascha Holzhauer <Sascha.Holzhauer@uni-kassel.de>
"""
import gettext
import os
from helpers.config import settings

localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "")
translate = gettext.translation(
    "ahoi", localedir, fallback=True, languages=settings.eval.language
)
_ = translate.gettext
