"""
A module for defining job and service data structures.

This module provides the `Job` dataclass, which encapsulates all necessary 
information for a task to be performed by an intermediary agent for a 
houseowner. It also includes the `IService` interface for type hinting services.

:Authors:
 - Sören Lohr
 - Ivan Digel <ivan.digel@uni-kassel.de>

"""
from dataclasses import dataclass
from mesa import Agent


class IService:
    """
    Represents an interface for services offered by intermediary agents.
    """
    ...


@dataclass
class Job:
    """A data class representing a job to be performed by an intermediary.

    Attributes
    ----------
    job_id : str
        A unique identifier for the job.
    customer : Agent
        The agent (typically a Houseowner) who requested the job.
    service : IService
        The service that is performing the job.
    duration : int, optional
        The time (in simulation steps) required to complete the job.
    """
    job_id: str
    customer: Agent
    service: IService
    duration: int = 1
