#!/usr/bin/env python

from actions.action import Action
from utility.common import launch
import os
import glob

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Pak(Action):
    """
    Pak Action
    Useful for custom paking of cooked assets. Ensure the assets you choose the pak are pre-cooked for the
    platform you are building for, or they might not mount properly.
    To cook assets, create a map containing the assets you would like to cook, and run the package action with
    only that map as content discovory.
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.content_root = kwargs['content_root'] if 'content_root' in kwargs else ''
        self.content_folder = kwargs['content_folder'] if 'content_folder' in kwargs else ''
        self.pak_name = kwargs['pak_name'] if 'pak_name' in kwargs else ''
        self.output_dir = kwargs['output_dir'] if 'output_dir' in kwargs else ''

        self.content_dir = os.path.join(self.content_root, self.content_folder)

    def verify(self):
        if self.content_root == '':
            return 'Content root is invalid!'
        if self.content_folder == '':
            return 'Content folder is invalid!'
        if self.content_dir == '' or not os.path.isdir(self.content_dir):
            if not os.path.isdir(os.path.join(self.config.uproject_dir_path, self.content_dir)):
                return 'Invalid Content folder for pak action. Set content_root and content_folder to create a valid' \
                       'content directory.'
        if self.pak_name == '':
            return 'pak_name is not set. Set the argument pak_name to a valid output pak name.'
        if self.output_dir == '':
            return 'output_dir is not set. Set the argument output_dir to a valid output path relative to the project.'
        return ''

    def run(self):
        self.error = self.verify()
        if self.error != '':
            return False

        full_content_dir = self.content_dir
        if not os.path.isabs(self.content_dir):
            full_content_dir = os.path.join(self.config.uproject_dir_path, self.content_dir)

        print('Glob Pattern: ' + (full_content_dir + os.path.sep + '**'))
        asset_paths = glob.glob(full_content_dir + os.path.sep + '**', recursive=True)

        pak_list_file_path = os.path.join(os.getcwd(), '{}_pak_list.txt'.format(self.pak_name))

        abs_content_root = self.content_root
        if not os.path.isdir(self.content_root):
            abs_content_root = os.path.join(self.config.uproject_dir_path, self.content_root)

        with open(pak_list_file_path, 'w') as fp:
            for asset_path in asset_paths:
                if os.path.isdir(asset_path):
                    continue
                reduced_root = asset_path.replace(abs_content_root, '')
                if reduced_root[0] == '\\' or reduced_root[0] == '/':
                    reduced_root = reduced_root[1:]
                content_asset_path = os.path.join('..\\..\\..', reduced_root)
                write_line = '"{0}" "{1}" -compress\n'.format(asset_path, content_asset_path.replace('\\', '/'))
                fp.write(write_line)

        unreal_pak_path = os.path.join(self.config.UE4EnginePath, 'Engine\\Binaries\\Win64\\UnrealPak.exe')
        if not os.path.isfile(unreal_pak_path):
            self.error = 'Unable to find path to UnrealPak.exe. Is it compiled?'
            return False

        cmd_args = [os.path.join(self.config.uproject_dir_path, self.output_dir, self.pak_name + '.pak'),
                    '-create={}'.format(pak_list_file_path),
                    '-encryptionini',
                    '-enginedir={}'.format(self.config.UE4EnginePath),
                    '-projectdir={}'.format(self.config.uproject_dir_path),
                    '-platform=Win64',
                    '-UTF8Output',
                    '-multiprocess']

        if launch(unreal_pak_path, cmd_args) != 0:
            self.error = 'Unable to pak!'
            return False
        return True
