"""Built-in AICC command registry."""

from . import doctor, job, skill, status, task


COMMAND_MODULES = (status, task, job, skill, doctor)
