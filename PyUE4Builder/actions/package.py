#!/usr/bin/env python

from actions.action import Action
from utility.common import launch, print_action, print_warning
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
    """

    # Other relative to project paths
    demo_switch_file_path = 'Source\\ShooterStream\\build_demo.txt'
    release_switch_file_path = 'Source\\ShooterStream\\build_release.txt'
    build_blacklist_dir = 'Build\\Win64'

    # Constants
    blacklist_file_name = 'PakBlacklist-{0}.txt'  # Param: Build name

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)

        self.pak_assets = kwargs['pak_assets'] if 'pak_assets' in kwargs else True
        self.nativize_assets = kwargs['nativize_assets'] if 'nativize_assets' in kwargs else True
        self.compressed_assets = kwargs['compressed_assets'] if 'compressed_assets' in kwargs else True
        self.no_debug_info = kwargs['no_debug_info'] if 'no_debug_info' in kwargs else False
        self.full_rebuild = kwargs['full_rebuild'] if 'full_rebuild' in kwargs else False
        self.no_editor_content = kwargs['no_editor_content'] if 'no_editor_content' in kwargs else False
        self.ignore_cook_errors = kwargs['ignore_cook_errors'] if 'ignore_cook_errors' in kwargs else False
        self.use_debug_editor_cmd = kwargs['use_debug_editor_cmd'] if 'use_debug_editor_cmd' in kwargs else False
        self.build_type = kwargs['build_type'] if 'build_type' in kwargs else 'standalone'
        self.maps = kwargs['maps'] if 'maps' in kwargs else []

    def run(self):
        if not self.config.check_environment():
            self.error = 'Environment is not ready for building or packaging!'
            return False

        click.secho('Building for client version {}'.format(self.config.version_str))

        valid_build_types = ['standalone', 'client', 'server']
        if self.build_type not in valid_build_types:
            print_warning('Unrecognized build type ({}) for package. Defaulting to "standalone".\n'
                          'Valid types={}'.format(self.build_type, valid_build_types))

        actual_build_path = self.config.build_path
        if self.build_type == 'client':
            actual_build_path += '_client'
        elif self.build_type == 'server':
            actual_build_path += '_server'

        if self.config.clean:
            # Kill the build directories
            def on_rm_error(func, path, exc_info):
                # path contains the path of the file that couldn't be removed
                # let's just assume that it's read-only and unlink it.
                del func  # Unused
                if exc_info[0] is not FileNotFoundError:
                    os.chmod(path, stat.S_IWRITE)
                    os.unlink(path)

            shutil.rmtree(actual_build_path, onerror=on_rm_error)

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
                    '-archivedirectory={}'.format(actual_build_path), '-package',
                    '-clientconfig={}'.format(self.config.configuration),
                    '-serverconfig={}'.format(self.config.configuration),
                    '-ue4exe={}'.format('UE4Editor-Win64-Debug-Cmd.exe' if self.use_debug_editor_cmd else
                                        'UE4Editor-Cmd.exe'),
                    '-prereqs', '-targetplatform=Win64', '-platform=Win64',
                    '-servertargetplatform=Win64', '-serverplatform=Win64',
                    '-build', '-CrashReporter', '-utf8output']

        if self.build_type == 'client':
            cmd_args.append('-client')
        elif self.build_type == 'server':
            cmd_args.extend(['-server', '-noclient'])

        if self.nativize_assets:
            cmd_args.append('-nativizeAssets')
        if self.pak_assets:
            cmd_args.append('-pak')
        if self.compressed_assets:
            cmd_args.append('-compressed')
        if self.no_debug_info:
            cmd_args.append('-nodebuginfo')
        if self.no_editor_content:
            cmd_args.append('-SkipCookingEditorContent')
        if self.ignore_cook_errors:
            cmd_args.append('-IgnoreCookErrors')

        if len(self.maps) > 0:
            cmd_args.append('-map={}'.format('+'.join(self.maps)))

        if self.config.clean or self.full_rebuild:
            cmd_args.append('-clean')
        else:
            cmd_args.extend(['-iterate', '-iterativecooking'])

        cmd_args.append('-compile')

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
