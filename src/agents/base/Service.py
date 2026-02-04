"""
Defines base classes for services provided by intermediary agents.

This module contains the abstract `Service` class, which provides a template 
for services like consultations or installations. It manages a job queue and 
handles the basic job lifecycle. It also includes a concrete `ConsultationService`
class that inherits from `Service`.

:Authors:
 - Sören Lohr
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>

"""
from abc import abstractmethod
from collections import deque
from agents.base.Job import Job, IService
import inspect

class Service(IService):
    """An abstract base class for services offered by intermediary agents.

    This class manages a queue of jobs, generates unique job IDs, and defines
    the interface for beginning, completing, and logging jobs. Subclasses
    must implement the `begin_job` method.

    Attributes
    ----------
    intermediary : Intermediary
        The intermediary agent providing the service.
    duration : int
        The default time in steps required to complete a job for this service.
    job_counter : int
        A counter for the number of jobs queued for this service.
    job_queue : deque
        A queue of `Job` objects waiting to be processed.
    """
    def __init__(self, intermediary=None, job_queue: deque = None):
        """Initializes a Service instance.

        Parameters
        ----------
        intermediary : Intermediary, optional
            The intermediary agent providing the service.
        job_queue : deque, optional
            An initial queue of jobs. Defaults to an empty deque.
        """
        self.intermediary = intermediary
        self.duration = 1
        self.job_counter = 0
        self.job_queue = job_queue if job_queue is not None else deque()
    
    def queue_job(self, houseowner):
        """Adds a new job to the service's queue for a given houseowner.

        Also prevents duplicate jobs from the same houseowner from being 
        added to the queue. It creates a `Job` object and appends to the
        job queue of the Service.

        Parameters
        ----------
        houseowner : Houseowner
            The houseowner agent requesting the service.
        """
        if any(job.customer.unique_id == houseowner.unique_id for job in self.job_queue):
            print(f"Houseowner {houseowner.unique_id} already has a queued consultation.")
            return

        self.job_counter += 1
        self.job_queue.append(Job(self.generate_id(), houseowner, self, self.duration))
    
    def generate_id(self):
        """Generates a unique ID for a new job.

        Returns
        -------
        str
            The formatted job ID, combining the intermediary ID, service name,
            and job counter.
        """
        return f"{self.intermediary.unique_id}-{type(self).__name__}-{self.job_counter}"

    @abstractmethod
    def begin_job(self):
        """An abstract method to begin processing a job.

        Subclasses must implement this method to define the specific actions 
        taken when a job starts.
        """
        ...

    def complete_job(self, job):
        """Finalizes a job and logs its completion.

        Records the details of the completed job in the model's datacollector
        for later analysis. Usually supplemented by complete_job
        of a specific intermediary.

        Parameters
        ----------
        job : Job
            The job that has been completed.
        """
        row = {
            "Step": self.intermediary.model.schedule.steps,
            "Job": job.job_id,
            "Intermediary": self.intermediary.unique_id,
            "Houseowner": job.customer.unique_id,
            "Service": type(job.service).__name__,
        }

        self.intermediary.model.datacollector.add_table_row(
            "Completed Intermediary Jobs", row
        )

    def save_queue_length(self):
        """Saves the current length of the job queue to the datacollector.

        This method is used for data collection at each simulation step to 
        track the workload of services.
        """
        row = {
            "Step": self.intermediary.model.schedule.steps,
            "Intermediary": self.intermediary.get_milieu(),
            "Intermediary ID": self.intermediary.unique_id,
            "Service": self.__class__.__name__,
            "Queue Length": len(self.job_queue),
        }

        self.intermediary.model.datacollector.add_table_row(
            "Intermediary Queue Length", row
        )


class ConsultationService(Service): 
    """A concrete implementation of a consultation service.

    This class serves as a specific type of `Service` for consultations. 
    It can be further subclassed or overridden to specify durations and behaviors 
    for different intermediary types (e.g., Plumber, EnergyAdvisor).
    """
    ...
