#!/usr/bin/env python

from utility.common import print_warning
import re

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
        self.config = config
        self.error = ''
        self.warnings = []
        self.build_meta = kwargs['build_meta'] if 'build_meta' in kwargs else None

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

    @staticmethod
    def replace_chars(chars, replace, str_in):
        for c in chars:
            if c in str_in:
                str_in = str_in.replace(c, replace)
        return str_in

    @staticmethod
    def replace_tagged_sections(path, var_class):
        re_exp = re.compile('({[0-9a-z_-]+})', re.IGNORECASE)
        splits = re_exp.split(path)
        path_out = path
        if len(splits):
            path_out = ''
            for split in splits:
                var_name = Action.replace_chars(['{', '}'], '', split)
                if hasattr(var_class, var_name):
                    path_out += getattr(var_class, var_name)
                else:
                    path_out += split
        return path_out

    def replace_tags(self, tagged_string):
        tagged_string = Action.replace_tagged_sections(tagged_string, self.config)
        if self.build_meta is not None:
            tagged_string = Action.replace_tagged_sections(tagged_string, self.build_meta)
        return tagged_string
