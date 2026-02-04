"""
Provides functions to retrieve project and system information.

This module contains utility functions for gathering metadata about the
project's version and the runtime environment. It can retrieve the current
Git version (either from a tag or commit hash) and monitor the process's
peak memory usage in a platform-independent manner.

:Authors:

 - Sascha Holzhauer <Sascha.Holzhauer@uni-kassel.de>

"""
import os
import platform

if os.name == 'posix':
    from resource import getrusage, RUSAGE_SELF

import subprocess

import gitinfo
import psutil


def get_git_version():
    """
    Retrieves current version from tag or commit identifier

    Returns
    -------
    str
        current version
    """
    gittag = (
        subprocess.check_output(["git", "tag", "--points-at", "HEAD"]).strip().decode()
    )
    if gittag != "":
        return gittag
    else:
        return gitinfo.get_git_info()["commit"][0:7]


def get_peak_memory_use():
    """
    Return the peak memory usage of the current process in bytes.

    Returns
    -------
    int: Peak memory usage in bytes
    """
    process = psutil.Process(os.getpid())
    if platform.system() == "Windows":  # Window
        return process.memory_info().peak_wset
    elif platform.system() == "Linux":
        return getrusage(RUSAGE_SELF).ru_maxrss / 1024
    elif os.name == "Darwin":
        return getrusage(RUSAGE_SELF).ru_maxrss
    else:  # Unix-based system
        raise ValueError(f"Not supported OS ({platform.system()})!")


if __name__ == "__main__":
    print(get_git_version())
    print(get_peak_memory_use())
