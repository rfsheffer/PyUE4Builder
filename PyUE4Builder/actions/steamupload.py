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


class Steamupload(Action):
    """
    Upload to steam action
    This action is designed to assist in your builds being uploaded to stream for release or testing purposes.
    TODO: Documentation and improvements!
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.set_live = kwargs['set_live'] if 'set_live' in kwargs else ''
        self.build_name = kwargs['build_name'] if 'build_name' in kwargs else ''

        # Example: "ThirdParty\\Steam\\tools\\ContentBuilder\\builder\\steamcmd.exe"
        self.builder_exe_path = kwargs['builder_exe_path'] if 'builder_exe_path' in kwargs else ''
        # Example: 'ThirdParty\\Steam\\tools\\ContentBuilder\\scripts\\'
        self.steam_app_dir = kwargs['steam_app_dir'] if 'steam_app_dir' in kwargs else ''
        # Example: 'ThirdParty\\Steam\\tools\\ContentBuilder\\scripts\\app_build_626250.vdf'
        self.steam_app_template = kwargs['steam_app_template'] if 'steam_app_template' in kwargs else ''
        # Example: 'WindowsNoEditor\\Engine\\Extras\\Redist\\en-us\\steam_redist_installscript.vdf'
        self.install_script_rel_path = kwargs['install_script_rel_path'] if 'install_script_rel_path' in kwargs else ''

    def verify(self):
        if STEAMWORKS_PASS_ENV_VAR not in os.environ:
            return 'Steamworks password not on environment!'
        if STEAMWORKS_USER_ENV_VAR not in os.environ:
            return 'Steamworks user not on environment!'
        if self.build_name == '' or not os.path.isdir(os.path.join(self.config.builds_path, self.build_name)):
            return 'Invalid build name supplied "{}". ' \
                   'Check name and ensure package folder exists!'.format(self.build_name)
        return ''

    def run(self):
        if self.config.clean:
            return True

        if self.config.clean:
            return True

        template_file_path = os.path.join(self.config.uproject_dir_path, self.steam_app_template)

        auto_file_path = os.path.join(self.config.uproject_dir_path,
                                      self.steam_app_dir,
                                      '{}_build.vdf'.format(self.config.uproject_name.lower()))

        self.create_app_build_script(template_file_path,
                                     auto_file_path,
                                     '..\\..\\..\\..\\..\\builds\\{}'.format(self.build_name),
                                     '{} Version {}'.format(self.config.uproject_name, self.config.version_str),
                                     self.set_live)

        try:
            steam_app_id_name = 'steam_appid.txt'
            shutil.copy2(os.path.join(self.config.uproject_dir_path, steam_app_id_name),
                         os.path.join(self.config.builds_path,
                                      '{}\\steam_appid.txt'.format(self.build_name)))
            if self.install_script_rel_path != '':
                shutil.copy2(os.path.join(self.config.uproject_dir_path, 'steam_redist_installscript.vdf'),
                             os.path.join(self.config.builds_path,
                                          self.install_script_rel_path))
            print_action('Steam required files inserted into build')
        except Exception:
            pass

        print_action('Uploading {} Build to Steam'.format(self.config.uproject_name))
        cmd_args = ['+login',
                    os.environ[STEAMWORKS_USER_ENV_VAR],
                    os.environ[STEAMWORKS_PASS_ENV_VAR],
                    '+run_app_build',
                    '..\\scripts\\{}_build.vdf'.format(self.config.uproject_name.lower()),
                    '+quit']

        if launch(os.path.join(self.config.uproject_dir_path, self.builder_exe_path), cmd_args) != 0:
            self.error = 'Unable to upload build {} to steam!'.format(self.config.uproject_name)
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
