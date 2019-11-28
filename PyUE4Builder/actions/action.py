#!/usr/bin/env python

from utility.common import print_warning

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Action(object):
    """
    The Base Action of all actions
    Override the run function and perform this action.
    Use kwargs to fetch passed in arguments and meta specified in the build script
    It is expected that your action can deal with two cases [build and clean].
    Use config.clean to determine the type of action to take.
    """
    def __init__(self, config, **kwargs):
        del kwargs
        self.config = config
        self.error = ''
        self.warnings = []

    @staticmethod
    def get_arg_docs():
        """
        Return documentation of the arguments this action takes
        :return: Documentation dictionary, argument=key, documentation=value
        """
        return {
        }

    def verify(self):
        """
        Called to verify if the arguments passed to this action are enough to
        complete the action in some meaningful way.
        :return: empty string if action can be completed, string describing problem if not
        """
        return ''

    def run(self):
        """
        The actions execution.
        An error message is stored in self.error if execution fails.
        :return: True if execution completed successfully. False if not.
        """
        return False

    def warning(self, msg):
        """
        Add a warning to output from this action. Prints the warning to screen and saves it for later summary.
        :param msg: The warning message
        """
        self.warnings.append(msg)
        print_warning(msg)
