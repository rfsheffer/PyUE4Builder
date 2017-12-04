#!/usr/bin/env python

from actions.action import Action
from utility.common import get_visual_studio_version, launch, print_action

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Build(Action):
    """
    Build action.
    This action is used to build unreal programs.
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.build_name = kwargs["build_name"]
        self.uproj_path = '' if "uproj_path" not in kwargs else kwargs["uproj_path"]

    def run(self):
        print_action('{} {}'.format('Building' if not self.config.clean else 'Cleaning', self.build_name))
        build_tool_path = self.config.UE4BuildBatchPath if not self.config.clean else self.config.UE4CleanBatchPath

        cmd_args = [self.build_name, 'Win64', self.config.configuration]
        if self.uproj_path != '':
            cmd_args.append(self.uproj_path)
        cmd_args += ['-NoHotReload', '-waitmutex']
        if get_visual_studio_version() == 2017:
            cmd_args.append('-2017')

        if launch(build_tool_path, cmd_args) != 0:
            self.error = 'Failed to build the Unreal Engine!'
            return False
        return True
