#!/usr/bin/env python

import os
import stat
import shutil
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
        self.force_clean = kwargs["force_clean"] if "force_clean" in kwargs else False

    def verify(self):
        if self.config.editor_running:
            return 'Cannot build "{}" because editor is running!'.format(self.build_name)
        return ''

    def run(self):
        self.error = self.verify()
        if self.error != '':
            return False

        build_name = self.build_name
        if self.is_game_project:
            # project based builds require the project name appended
            build_name = self.config.uproject_name + build_name

        print_action('{} {}'.format('Building' if not self.config.clean else 'Cleaning', build_name))

        cmd_args = [build_name, 'Win64', self.config.configuration]
        if self.is_game_project:
            cmd_args.append(self.config.uproject_file_path)
        cmd_args += ['-NoHotReload', '-waitmutex']
        if get_visual_studio_version() == 2017:
            cmd_args.append('-2017')

        # Do any pre cleaning
        if self.config.clean or self.force_clean:
            if self.is_game_project:
                self.clean_game_project_folder()
            else:
                if launch(self.config.UE4CleanBatchPath, cmd_args) != 0:
                    self.error = 'Failed to clean project {}'.format(build_name)
                    return False

        # Do the actual build
        if launch(self.config.UE4BuildBatchPath, cmd_args) != 0:
            self.error = 'Failed to build "{}"!'.format(build_name)
            return False
        return True

    def clean_game_project_folder(self):
        """
        Backstory:
            We need to manually clean the game project folder because calling clean normally also forcibly cleans
            the engine which is always un-desirable since the engine would have been cleaned and re-built already
            prior to the game build step. This is an Unreal issue which I hope they resolve one day.
        """
        # Kill the build directories
        def on_rm_error(func, path, exc_info):
            # path contains the path of the file that couldn't be removed
            # let's just assume that it's read-only and unlink it.
            del func  # Unused
            if exc_info[0] is not FileNotFoundError:
                os.chmod(path, stat.S_IWRITE)
                os.unlink(path)

        # First delete the intermediates of the game project
        shutil.rmtree(os.path.join(self.config.uproject_dir_path, 'Intermediate\\Build'), onerror=on_rm_error)

        # Traverse the plugins and delete the plugins intermediates as well
        plugins_dir_path = os.path.join(self.config.uproject_dir_path, 'Plugins')
        plugin_dirs = [os.path.join(self.config.uproject_dir_path, 'Plugins', plugin_dir)
                       for plugin_dir in os.listdir(plugins_dir_path)]
        for plugin_dir in plugin_dirs:
            shutil.rmtree(os.path.join(plugin_dir, 'Intermediate\\Build'), onerror=on_rm_error)
