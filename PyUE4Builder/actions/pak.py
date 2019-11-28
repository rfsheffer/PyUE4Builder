#!/usr/bin/env python

from actions.action import Action
from utility.common import launch
import os
import glob

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Pak(Action):
    """
    Pak Action
    Useful for custom paking of cooked assets. Ensure the assets you choose to pak are pre-cooked for the
    platform you are building for, or they might not mount properly.
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.content_dir = kwargs['content_dir'] if 'content_dir' in kwargs else ''
        self.content_paths = kwargs['content_paths'] if 'content_paths' in kwargs else []
        self.asset_root_path = kwargs['asset_root_path'] if 'asset_root_path' in kwargs else '../../../'
        self.pak_name = kwargs['pak_name'] if 'pak_name' in kwargs else ''
        self.output_dir = kwargs['output_dir'] if 'output_dir' in kwargs else ''

        if not os.path.isabs(self.content_dir):
            self.content_dir = os.path.join(self.config.uproject_dir_path, self.content_dir)

    @staticmethod
    def get_arg_docs():
        return {
            'content_dir': 'The cooked content directory which all content_paths are relative to.',
            'content_paths': 'Relative paths from content_dir to the asset folders you want included in the pak.',
            'asset_root_path': 'This is the root path of all content_paths assets. This path is commonly set to'
                               '../../../MyContent and in engine a content mount point is set to be able to read'
                               'content from that path. See FPackageName::RegisterMountPoint in Unreal source'
                               'for details.',
            'pak_name': 'The name to assign to the pak file',
            'output_dir': 'The output directory for the pak file'
        }

    def verify(self):
        if self.content_dir == '':
            return 'Content path is invalid!'
        if not os.path.isdir(self.content_dir):
            return 'Invalid Content folder for pak action. Set content_root and content_folder to create a valid' \
                   'content directory.'
        if self.pak_name == '':
            return 'pak_name is not set. Set the argument pak_name to a valid output pak name.'
        if self.output_dir == '':
            return 'output_dir is not set. Set the argument output_dir to a valid output path relative to the project.'
        return ''

    def run(self):
        pak_list_file_path = os.path.join(os.getcwd(), '{}_pak_list.txt'.format(self.pak_name))
        with open(pak_list_file_path, 'w') as fp:
            for content_path in self.content_paths:
                asset_paths = glob.glob(os.path.join(self.content_dir, content_path) + os.path.sep + '**',
                                        recursive=True)
                for asset_path in asset_paths:
                    if os.path.isdir(asset_path):
                        continue
                    reduced_root = asset_path.replace(self.content_dir, '')
                    if reduced_root[0] == '\\' or reduced_root[0] == '/':
                        reduced_root = reduced_root[1:]
                    content_asset_path = os.path.join(self.asset_root_path, reduced_root)
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
                    '-platform={}'.format(self.config.platform),
                    '-UTF8Output',
                    '-multiprocess']

        if launch(unreal_pak_path, cmd_args) != 0:
            self.error = 'Unable to pak!'
            return False
        return True
