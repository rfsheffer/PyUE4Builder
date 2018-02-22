#!/usr/bin/env python

from actions.action import Action
import os
import contextlib
import re
import shutil

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Copy(Action):
    """
    Copy Action
    An action designed to copy file/s as part of a build process.
    TODO: Setup wildcard like copying? Take advantage of a copy module with a lot of options.
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.copy_items = kwargs['copy'] if 'copy' in kwargs else []

    @staticmethod
    def replace_path_sections(path, var_class):
        re_exp = re.compile('{([0-9a-z_-]+)}', re.IGNORECASE)
        splits = re_exp.split(path)
        path_out = path
        if len(splits):
            path_out = ''
            for split in splits:
                if hasattr(var_class, split):
                    path_out += getattr(var_class, split)
                else:
                    path_out += split
        return path_out

    def verify(self):
        if not len(self.copy_items):
            return 'No items to copy!'
        for item in self.copy_items:
            if type(item) is not list or len(item) != 2:
                return 'Invalid copy item found in copy list!'

            item[0] = self.replace_path_sections(item[0], self.config)
            item[1] = self.replace_path_sections(item[1], self.config)

            if not os.path.isfile(item[0]):
                return 'Copy item ({}) does not exist!'.format(item[0])
        return ''

    def run(self):
        for item in self.copy_items:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(item[1])
            os.makedirs(os.path.dirname(item[1]), exist_ok=True)
            print('Copying {} to {}'.format(item[0], item[1]))
            shutil.copy2(item[0], item[1])
        return True


if __name__ == "__main__":
    class VarClassTest(object):
        def __init__(self):
            self.HI2_there = "some\\cool\\path"
            self.three = "another\\cool\\path"
    print(Copy.replace_path_sections('hello\\{HI2_there}\\then\\there\\were\\{three}\\bla.exe', VarClassTest()))
    print(Copy.replace_path_sections('hello\\then\\there\\were\\three.exe', VarClassTest()))
