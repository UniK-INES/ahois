"""
This module modifies how warnings are handled and displayed throughout the
project. Based on configuration settings, it can simplify the format of
warning messages to make them more readable or escalate specific types of
warnings into exceptions to enforce stricter code quality during debugging.

:Authors:
 - Sascha Holzhauer <sascha.holzhauer@iee.fraunhofer.de>

"""
import warnings
import builtins
from helpers.config import settings


def custom_formatwarning(msg, *args, **kwargs):
    """
    This function overrides the default multi-line warning format. It
    discards all parts of the warning except for the message itself and
    prepends the message with its type (e.g., 'DeprecationWarning').

    Parameters
    ----------
    msg: Warning
        The warning message object.
    *args: tuple
        Additional arguments (ignored).
    **kwargs: dict
        Additional keyword arguments (ignored).

    Returns
    -------
    str
        The formatted, single-line warning string.
    """
    # ignore everything except the message
    return type(msg).__name__ + ": " + str(msg) + "\n"


if not settings.debug.output_detailed_warnings:
    warnings.formatwarning = custom_formatwarning

if settings.debug.output_warnings_as_errors:
    warnings.filterwarnings(
        "error", category=getattr(builtins, settings.debug.warningsforerrors)
    )
