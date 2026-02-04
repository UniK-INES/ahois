"""
Provides a custom Dynaconf loader that merges settings without overriding.

This module contains a custom loader function for the Dynaconf settings
management library. Unlike the default loaders which override existing keys,
this loader implements a "fill-in" logic. It reads settings from specified
TOML files and only adds keys (or sub-keys) that are not already present in the
settings object. This is particularly useful for loading default values that
should not overwrite any user-specified configurations.

Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>

"""
from dynaconf.base import SourceMetadata
from dynaconf.utils import upperfy
from dynaconf.constants import TOML_EXTENSIONS
from dynaconf.loaders.base import BaseLoader
from dynaconf.vendor import tomllib

def load(obj, env=None, silent=True, key=None, filename=None):
    """
    Loads settings from TOML files without overriding existing values.

    This function iterates through a list of filenames defined in the settings
    variable `EVAL.AHID_SETTINGS_FILES`. For each file, it parses the content
    and merges it into the main settings object (`obj`) under the condition
    that the keys do not already exist.

    The merging logic is as follows:
    1. If a top-level key from the file is not in `obj`, the key and its
       entire value are added.
    2. If a top-level key exists, the function checks its sub-keys. Only the
       sub-keys from the file that are not already in `obj[key]` are added.

    Parameters
    ----------
    obj : dynaconf.base.LazySettings
        The Dynaconf settings instance to be loaded into.
    env : str, optional
        The environment to load. This parameter is part of the standard loader
        signature but is not used by this function. Defaults to None.
    silent : bool, optional
        If True, exceptions during file loading (e.g., file not found) are
        suppressed. Defaults to True.
    key : str, optional
        Load only this specific key. This parameter is not used by this
        function. Defaults to None.
    filename : str, optional
        A specific file to be loaded. This parameter is not used; the function
        relies on the `EVAL.AHID_SETTINGS_FILES` list in `obj`. Defaults to None.

    """
    for filename in obj.get("EVAL.AHID_SETTINGS_FILES", []):
        found_file = obj.find_file(filename)
        if not found_file:
            continue
        
        # IMPLEMENT YOUR LOGIC HERE
        # parse the file data
        # traverse the data checking if is already set on `obj`
        # build a dictionary with the data to be merged omiting the 
        # existing data to avoid override.
        
        loader = BaseLoader(
            obj=obj,
            env=None,
            identifier="toml",
            extensions=TOML_EXTENSIONS,
            file_reader=tomllib.load,
            string_reader=tomllib.loads,
            opener_params={"mode": "rb"},
            validate=False,
        )
        
        fdata = loader.get_source_data([found_file])[found_file]
        data = {"dynaconf_merge": True}
        
        for key, value in fdata.items():
            if not obj.exists(key):
                data[key] = value
            else:
                data[key] = {}
                for subkey, subvalue in value.items():
                    if subkey not in obj[key]:
                        data[key][subkey] = subvalue
                
        # UPDATE THE SETTINGS WITH DATA
        source_metadata = SourceMetadata("plugin", found_file, "default")
        obj.update(data, loader_identifier=source_metadata)
            
            
if __name__ == '__main__':
    pass