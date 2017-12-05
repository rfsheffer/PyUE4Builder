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
        self.is_game_project = kwargs["is_game_project"] if "is_game_project" in kwargs else False

    def run(self):
        build_name = self.build_name
        if self.is_game_project:
            # project based builds require the project name appended
            build_name = self.config.uproject_name + build_name

        print_action('{} {}'.format('Building' if not self.config.clean else 'Cleaning', build_name))
        build_tool_path = self.config.UE4BuildBatchPath if not self.config.clean else self.config.UE4CleanBatchPath

        cmd_args = [build_name, 'Win64', self.config.configuration]
        if self.is_game_project:
            cmd_args.append(self.config.uproject_file_path)
        cmd_args += ['-NoHotReload', '-waitmutex']
        if get_visual_studio_version() == 2017:
            cmd_args.append('-2017')

        if launch(build_tool_path, cmd_args) != 0:
            self.error = 'Failed to build the Unreal Engine!'
            return False
        return True
