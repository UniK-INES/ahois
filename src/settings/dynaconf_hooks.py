"""
Post-processing of dynaconf settings to allow overriding list_lang entries
in eval.language.

:Authors:

 - Sascha Holzhauer <Sascha.Holzhauer@uni-kassel.de>
 
"""


def post(settings):
    """
    A post-hook for Dynaconf to enable list-type setting overrides.
    This function is automatically executed by Dynaconf after settings are loaded.
    It provides a mechanism to completely replace list-based settings
    (specifically `eval.language`) instead of the default merging behaviour.

    Parameters
    ----------
    settings : dynaconf.LazySettings
        The Dynaconf settings object, passed automatically by the hook runner.

    Returns
    -------
    dict
        The modified settings, converted to a dictionary as required by
        Dynaconf post-hooks.

    """
    fields = ["eval.language"]
    for field in fields:
        clear = False
        if settings.exists(field):
            list_lang = settings.get("eval.language").to_list()
            if "CLEAR" in list_lang:
                newlist = []
                for item in list_lang:
                    if item == "END":
                        clear = False
                    if clear:
                        newlist.append(item)
                    if item == "CLEAR":
                        clear = True
                settings.set(field, newlist, merge=False)
    return settings.as_dict()
