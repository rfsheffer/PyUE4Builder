#!/usr/bin/env python

from actions.action import Action
from utility.common import launch
import os

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Cook(Action):
    """
    Cook action.
    An action designed to invoke the Unreal Engines cook commandlet
    TODO: This action is EXPERIMENTAL
    """

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.maps = kwargs['maps'] if 'maps' in kwargs else []
        self.cook_dirs = kwargs['cook_dirs'] if 'cook_dirs' in kwargs else []
        self.cultures = kwargs['cultures'] if 'cultures' in kwargs else []
        self.output_dir = kwargs['output_dir'] if 'output_dir' in kwargs else []

    @staticmethod
    def get_arg_docs():
        return {
            "maps": "(optional) List of maps to cook",
            "cook_dirs": "(optional) Directories to unconditionally cook",
            "cultures": "(optional) List of cultures to cook the content for",
            "output_dir": "Cooked asset output directory",
        }

    def verify(self):
        if not os.path.isdir(self.output_dir):
            return 'Invalid output directory!'
        return ''

    def run(self):
        exe_path = 'UE4Editor-Win64-Debug-Cmd.exe' if self.config.debug else 'UE4Editor-Cmd.exe'
        exe_path = os.path.join(self.config.UE4EnginePath, 'Engine/Binaries/Win64', exe_path)
        if not os.path.isfile(exe_path):
            self.error = 'Unable to resolve path to unreal cmd "{}"'.format(exe_path)
            return False

        # Cook command parameters
        cmd_args = ['-run=Cook']

        for map_name in self.maps:
            cmd_args.append('-Map={}'.format(map_name))

        for dir_name in self.cook_dirs:
            cmd_args.append('-CookDir={}'.format(dir_name))

        if len(self.cultures) > 0:
            cmd_args.append('-CookCultures={}'.format('+'.join(self.cultures)))

        cmd_args.append('-NoLogTimes')

        # General Parameters
        cmd_args.extend(['-TargetPlatform={}'.format(self.config.platform), '-Unversioned'])

        cmd_args.append('-output_dir={}'.format(self.output_dir))

        if self.config.debug:
            cmd_args.append('-debug')

        if launch(exe_path, cmd_args) != 0:
            self.error = 'Unable to complete cook action. Check output.'
            return False

        return True
