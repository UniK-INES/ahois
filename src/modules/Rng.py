"""
Manages random number generation to ensure model reproducibility.

This module provides a suite of functions that serve as access points to
separate, seeded random number generators (RNGs). By using distinct RNG
streams for different model components (e.g., model setup, agent behaviour), 
it prevents a change in one stochastic process
from affecting the outcomes of others.

Each function initialises a singleton NumPy `Generator` instance on its first
call, using a specific seed from the project's configuration file. All
subsequent calls return the same instance. This ensures that the sequence of
random numbers for each stream is consistent across identical simulation runs.
The module also includes an optional debugging utility to log the call stack
each time an RNG is accessed.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>

"""
import numpy as np
import os
import inspect
import traceback
import logging
from helpers.config import settings

model_init_rng = None
model_run_rng = None
house_init_rng = None
houseowner_run_rng = None
plumber_run_rng = None
milieu_init_rng = None
heating_init_rng = None
information_source_run_rng = None

run = 1
counter = 0
initialised = False


def init():
    """
    Initialise the output directory for RNG invocation logs.

    This is an internal helper function called by `print_stacktrace` on its
    first invocation to ensure the target directory for logging exists.
    """
    global initialised
    if not initialised:
        os.makedirs(os.path.join(settings.output.randomstreaminvocations_folder), exist_ok=True)
        initialised = True

def rng_model_init(message: str = ""):
    """
    Provides the RNG instance for model initialisation.
    
    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for model initialisation.
    """
    global model_init_rng
    if model_init_rng is None:
        model_init_rng = np.random.default_rng(seed=settings.seeds.model_init)
    #print_stacktrace(name=settings.output.logger_model_init, message=message)
    return model_init_rng


def rng_model_run(message: str = ""):
    """
    Provides the RNG instance for the main model run loop.

    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for the model's run phase.
    """
    global model_run_rng
    if model_run_rng is None:
        model_run_rng = np.random.default_rng(seed=settings.seeds.model_run)
    #print_stacktrace(name=settings.output.logger_model_run, message=message)
    return model_run_rng


def rng_house_init(message: str = ""):
    """
    Provides the RNG instance for the initialisation of instances
    of the House class.
    
    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for model initialisation.
    """
    global house_init_rng
    if house_init_rng is None:
        house_init_rng = np.random.default_rng(seed=settings.seeds.house_init)
    #print_stacktrace(name=settings.output.logger_house_ini, message=message)
    return house_init_rng


def rng_houseowner_run(message: str = ""):
    """
    Provides the RNG instance for the Houseowner behaviour-related
    random processes.
    
    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for model initialisation.
    """
    global houseowner_run_rng
    if houseowner_run_rng is None:
        houseowner_run_rng = np.random.default_rng(seed=settings.seeds.houseowner_run)
    #print_stacktrace(name=settings.output.logger_houseowner_run, message=message)
    return houseowner_run_rng


def rng_plumber_run(message: str = ""):
    """
    Provides the RNG instance for the Plumber behaviour-related
    random processes.
    
    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for model initialisation.
    """
    global plumber_run_rng
    if plumber_run_rng is None:
        plumber_run_rng = np.random.default_rng(seed=settings.seeds.plumber_run)
    #print_stacktrace(name=settings.output.logger_plumber_run, message=message)
    return plumber_run_rng


def rng_milieu_init(message: str = ""):
    """
    Provides the RNG instance for the initialisation of the Houseowner milieu.
    
    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for model initialisation.
    """
    global milieu_init_rng
    if milieu_init_rng is None:
        milieu_init_rng = np.random.default_rng(seed=settings.seeds.milieu_init)
    #print_stacktrace(name=settings.output.logger_milieu_init, message=message)
    return milieu_init_rng


def rng_heating_init(message: str = ""):
    """
    Provides the RNG instance for the initialisation of the Heating_system
    related initialisation.
    
    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for model initialisation.
    """
    global heating_init_rng
    if heating_init_rng is None:
        heating_init_rng = np.random.default_rng(seed=settings.seeds.heating_init)
    #print_stacktrace(name=settings.output.logger_heating_init, message=message)
    return heating_init_rng


def rng_information_source_run(message: str = ""):
    """
    Provides the RNG instance for the interaction between Houseowners and
    information sources.
    
    Parameters
    ----------
    message : str, optional
        A message to include in the stack trace log for debugging context,
        by default "".

    Returns
    -------
    numpy.random.Generator
        The singleton RNG instance for model initialisation.
    """
    global information_source_run_rng
    if information_source_run_rng is None:
        information_source_run_rng = np.random.default_rng(
            seed=settings.seeds.information_source_run
        )
    #print_stacktrace(name=settings.output.logger_information_source_run, message=message)
    return information_source_run_rng


def print_stacktrace(name="", message: str = ""):
    """
    Log the current call stack to a file for debugging.
    When enabled via `settings.output.randomstreaminvocations`, this function
    is called by an RNG provider to record the sequence of function calls
    that led to the request for a random number. It helps trace the exact source of
    randomness and verify that the correct RNG streams are being used.

    Parameters
    ----------
    name : str, optional
        The prefix for the log file's name, by default "".
    message : str, optional
        A contextual message to include in the log entry, by default "".
    """
    if settings.output.randomstreaminvocations:
        init()
        global counter
        counter += 1
        with open(os.path.join(settings.output.randomstreaminvocations_folder, 
                               name + str(run) + ".txt"), "a") as f:
            print(f"<------- {counter:7d} > " + message, file=f)
            stack = inspect.stack()
            traceback.print_stack(
                limit=-(len(stack) - settings.output.randomstream_cutentries), file=f
            )
            print("-------> ", file=f)
            