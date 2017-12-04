#!/usr/bin/env python

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
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

    def run(self):
        return False
