#!/usr/bin/env python

from actions.action import Action
from utility.common import launch, print_action
import click
import shutil
import os
import stat

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Package(Action):
    """
    Package action.
    This action is used to build and package a project.
    TODO: This should be broken up into sub actions (build, cook, package) for finer grained control.
    """

    # Other relative to project paths
    demo_switch_file_path = 'Source\\ShooterStream\\build_demo.txt'
    release_switch_file_path = 'Source\\ShooterStream\\build_release.txt'
    build_blacklist_dir = 'Build\\Win64'

    # Constants
    blacklist_file_name = 'PakBlacklist-{0}.txt'  # Param: Build name

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)

    def run(self):
        if not self.config.check_environment():
            self.error = 'Environment is not ready for building or packaging!'
            return False

        click.secho('Building for client version {}'.format(self.config.version_str))

        if self.config.clean:
            # Kill the build directories
            def on_rm_error(func, path, exc_info):
                # path contains the path of the file that couldn't be removed
                # let's just assume that it's read-only and unlink it.
                del func  # Unused
                if exc_info[0] is not FileNotFoundError:
                    os.chmod(path, stat.S_IWRITE)
                    os.unlink(path)

            shutil.rmtree(self.config.build_path, onerror=on_rm_error)

        demo_build = self.config.package_type == 'Demo'
        release_build = self.config.package_type == 'Release'

        cap_build_name = self.config.package_type.title()
        print_action('Building {} Build'.format(cap_build_name))
        # *************************************************
        # DEMO SWITCH
        if not demo_build and os.path.isfile(os.path.join(self.config.uproject_dir_path, self.demo_switch_file_path)):
            os.unlink(os.path.join(self.config.uproject_dir_path, self.demo_switch_file_path))
        elif demo_build and not os.path.isfile(os.path.join(self.config.uproject_dir_path, self.demo_switch_file_path)):
            print_action('Flipping demo build switch')
            fp = open(os.path.join(self.config.uproject_dir_path, self.demo_switch_file_path), 'w')
            fp.close()
        # *************************************************
        # RELEASE SWITCH
        if not release_build and os.path.isfile(os.path.join(self.config.uproject_dir_path,
                                                             self.release_switch_file_path)):
            os.unlink(os.path.join(self.config.uproject_dir_path, self.release_switch_file_path))
        elif release_build and not os.path.isfile(os.path.join(self.config.uproject_dir_path,
                                                               self.release_switch_file_path)):
            print_action('Flipping release build switch')
            fp = open(os.path.join(self.config.uproject_dir_path, self.release_switch_file_path), 'w')
            fp.close()

        # If Demo, create demo content blacklist
        build_blacklist_file_path = os.path.join(self.config.uproject_dir_path,
                                                 self.build_blacklist_dir,
                                                 self.blacklist_file_name.format(self.config.configuration))
        if demo_build:
            print_action('Setting up demo blacklist for configuration {}'.format(self.config.configuration))
            if os.path.isfile(build_blacklist_file_path):
                os.unlink(build_blacklist_file_path)
            os.makedirs(os.path.join(self.config.uproject_dir_path, self.build_blacklist_dir), exist_ok=True)
            shutil.copyfile(os.path.join(self.config.uproject_dir_path, 'demo_map_blacklist.txt'),
                            os.path.join(build_blacklist_file_path))

        cmd_args = ['-ScriptsForProject={}'.format(self.config.uproject_file_path),
                    'BuildCookRun', '-nocompileeditor', '-NoHotReload', '-nop4',
                    '-project={}'.format(self.config.uproject_file_path), '-cook', '-stage', '-archive',
                    '-archivedirectory={}'.format(self.config.build_path), '-package',
                    '-clientconfig={}'.format(self.config.configuration), '-ue4exe=UE4Editor-Cmd.exe',
                    '-pak', '-nativizeAssets', '-prereqs', '-targetplatform=Win64', '-platform=Win64',
                    '-build', '-CrashReporter', '-utf8output', '-compile']
        if self.config.clean:
            cmd_args.append('-clean')

        print_action('Building, Cooking, and Packaging {} Build'.format(cap_build_name))
        if launch(self.config.UE4RunUATBatPath, cmd_args) != 0:
            self.error = 'Unable to build {}!'.format(self.config.package_type)
            return False

        # Don't leave the demo switch around so it doesn't contaminate local builds
        if os.path.isfile(os.path.join(self.config.uproject_dir_path, self.demo_switch_file_path)):
            os.unlink(os.path.join(self.config.uproject_dir_path, self.demo_switch_file_path))

        if os.path.isfile(os.path.join(self.config.uproject_dir_path, self.release_switch_file_path)):
            os.unlink(os.path.join(self.config.uproject_dir_path, self.release_switch_file_path))

        # Don't leave blacklist around
        if os.path.isfile(build_blacklist_file_path):
            os.unlink(build_blacklist_file_path)

        return True
