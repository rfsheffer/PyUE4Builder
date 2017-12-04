#!/usr/bin/env python

import os
import shutil
from actions.action import Action
from utility.common import print_action, launch

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer"]

# Environment Variables which need to be set to the relavant strings for this script to function
STEAMWORKS_USER_ENV_VAR = 'STEAMWORKS_USER'
STEAMWORKS_PASS_ENV_VAR = 'STEAMWORKS_PASS'

# TODO: Move these into the configuration
builder_exe_path = "ThirdParty\\Steam\\tools\\ContentBuilder\\builder\\steamcmd.exe"
steam_app_dir = 'ThirdParty\\Steam\\tools\\ContentBuilder\\scripts\\'
steam_app_template = 'ThirdParty\\Steam\\tools\\ContentBuilder\\scripts\\app_build_626250.vdf'
steam_demo_app_template = 'ThirdParty\\Steam\\tools\\ContentBuilder\\scripts\\app_build_726310.vdf'
install_script_rel_path = 'WindowsNoEditor\\Engine\\Extras\\Redist\\en-us\\steam_redist_installscript.vdf'


class Steamupload(Action):
    """
    Upload to steam action
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.set_live = kwargs['set_live'] if 'set_live' in kwargs else ''

    def run(self):
        if self.config.clean:
            return True
        if self.config.package_type != 'Package':
            self.error = 'Steam Upload is only run on package builds!'
            return False
        if STEAMWORKS_PASS_ENV_VAR not in os.environ:
            self.error = 'Steamworks password not on environment!'
            return False
        if STEAMWORKS_USER_ENV_VAR not in os.environ:
            self.error = 'Steamworks user not on environment!'
            return False

        demo_build = self.config.package_type == 'Demo'
        release_build = self.config.package_type == 'Release'

        template_file_path = os.path.join(self.config.uproject_dir_path,
                                          steam_demo_app_template if demo_build else steam_app_template)

        auto_file_path = os.path.join(self.config.uproject_dir_path,
                                      steam_app_dir,
                                      '{}_build.vdf'.format(self.config.package_type.lower()))

        self.create_app_build_script(template_file_path,
                                     auto_file_path,
                                     '..\\..\\..\\..\\..\\builds\\{}\\WindowsNoEditor'.format(self.config.build_name),
                                     '{} Version {}'.format(self.config.package_type, self.config.version_str),
                                     self.set_live)

        try:
            steam_app_id_name = 'steam_appid_demo.txt' if demo_build else 'steam_appid.txt'
            shutil.copy2(os.path.join(self.config.uproject_dir_path, steam_app_id_name),
                         os.path.join(self.config.build_path, 'WindowsNoEditor\\steam_appid.txt'))
            shutil.copy2(os.path.join(self.config.uproject_dir_path, 'steam_redist_installscript.vdf'),
                         os.path.join(self.config.build_path, install_script_rel_path))
            print_action('Steam required files inserted into build')
        except Exception:
            pass

        print_action('Uploading {} Build to Steam'.format(self.config.package_type))
        cmd_args = ['+login',
                    os.environ[STEAMWORKS_USER_ENV_VAR],
                    os.environ[STEAMWORKS_PASS_ENV_VAR],
                    '+run_app_build',
                    '..\\scripts\\{}_build.vdf'.format(self.config.package_type.lower()),
                    '+quit']

        if launch(os.path.join(self.config.uproject_dir_path, builder_exe_path), cmd_args) != 0:
            self.error = 'Unable to upload build {} to steam!'.format(self.config.package_type)
            return False
        return True

    @staticmethod
    def create_app_build_script(template_file_path, auto_file_path, content_root, version_str, build_to_set_live=''):
        """
        We templatize from template_path to create a new build script with an auto generated description string
        and output to auto_file_path
        """
        new_file = ''
        with open(template_file_path, 'r') as fp:
            for line in fp.readlines():
                if '"desc"' in line:
                    new_file += '\t"desc" "{0}"\n'.format(version_str)
                elif '"setlive"' in line:
                    new_file += '\t"setlive" "{0}"\n'.format(build_to_set_live)
                elif '"contentroot"' in line:
                    new_file += '\t"contentroot" "{0}"\n'.format(content_root)
                else:
                    new_file += line
        if os.path.isfile(auto_file_path):
            os.unlink(auto_file_path)
        with open(auto_file_path, 'w') as fp:
            fp.write(new_file)
