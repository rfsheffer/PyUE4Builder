#!/usr/bin/env python

import os
import stat
import shutil
from actions.action import Action
from utility.common import get_visual_studio_version, launch, print_action

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Build(Action):
    """
    Build action.
    This action is used to build unreal programs.
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.build_name = kwargs['build_name'] if 'build_name' in kwargs else ''
        self.build_names = kwargs['build_names'] if 'build_names' in kwargs else ''
        self.force_clean = kwargs["force_clean"] if "force_clean" in kwargs else False

    @staticmethod
    def get_arg_docs():
        return {
            'build_name': 'The name of the project to build.',
            'build_names': 'Same as build_name but accepts a list of builds',
            'force_clean': 'Force this build/s to be cleaned, regardless of the global clean flag'
        }

    def verify(self):
        if len(self.build_name) == 0 and len(self.build_names) == 0:
            return 'No valid build name supplied to this action!'

        if self.config.editor_running:
            return 'Cannot build "{}" because editor is running!'.format(self.build_name)
        return ''

    def run(self):
        if len(self.build_name) != 0:
            if not self.do_build(self.build_name):
                return False

        if len(self.build_names) != 0:
            for build_name in self.build_names:
                if not self.do_build(build_name):
                    return False
        return True

    def do_build(self, build_name):
        # If the build starts with the project name, we know this is a game project being built
        is_game_project = build_name.startswith(self.config.uproject_name)

        print_action('{} {}'.format('Building' if not self.config.clean else 'Cleaning', build_name))

        cmd_args = [build_name, self.config.platform, self.config.configuration]
        if is_game_project:
            cmd_args.append(self.config.uproject_file_path)
        cmd_args += ['-NoHotReload', '-waitmutex']
        if self.config.engine_major_version == 4 and self.config.engine_minor_version <= 25:
            cmd_args.append('-VS{}'.format(get_visual_studio_version(self.config.get_suitable_vs_versions())))
        else:
            # Engine versions greater than 25 can determine visual studios location and will do it automatically.
            # We include -FromMsBuild which is common beyond version 25 but it is just a format specifier.
            cmd_args.append('-FromMsBuild')

        # Do any pre cleaning
        if self.config.clean or self.force_clean:
            if is_game_project:
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
        if self.build_name.endswith('Editor'):
            shutil.rmtree(
                os.path.join(self.config.uproject_dir_path,
                             'Intermediate\\Build\\{}\\UE4Editor'.format(self.config.platform)),
                onerror=on_rm_error)

        shutil.rmtree(
            os.path.join(self.config.uproject_dir_path,
                         'Intermediate\\Build\\{}\\{}'.format(self.config.platform, self.build_name)),
            onerror=on_rm_error)

        # Traverse the plugins and delete the plugins intermediates as well
        plugins_dir_path = os.path.join(self.config.uproject_dir_path, 'Plugins')
        plugin_dirs = [os.path.join(self.config.uproject_dir_path, 'Plugins', plugin_dir)
                       for plugin_dir in os.listdir(plugins_dir_path)]
        for plugin_dir in plugin_dirs:
            if self.build_name.endswith('Editor'):
                shutil.rmtree(
                    os.path.join(plugin_dir,
                                 'Intermediate\\Build\\{}\\UE4Editor'.format(self.config.platform)),
                    onerror=on_rm_error)
            shutil.rmtree(
                os.path.join(plugin_dir,
                             'Intermediate\\Build\\{}\\{}'.format(self.config.platform, self.build_name)),
                onerror=on_rm_error)
