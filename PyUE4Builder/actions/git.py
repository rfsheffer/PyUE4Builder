#!/usr/bin/env python

from actions.action import Action
import os
import stat
import shutil
from utility.common import print_action, push_directory, launch

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Git(Action):
    """
    Git Action
    An action for syncing a git repo to a specified folder
    """

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.branch_name = kwargs['branch'] if 'branch' in kwargs else ''
        self.repo_name = kwargs['repo'] if 'repo' in kwargs else ''
        self.output_folder = kwargs['output_folder'] if 'output_folder' in kwargs else ''
        self.rsa_path = kwargs['rsa_path'] if 'rsa_path' in kwargs else ''
        self.force_repull = kwargs['force_repull'] if 'force_repull' in kwargs else False
        self.disable_strict_hostkey_check = \
            kwargs['disable_strict_hostkey_check'] if 'disable_strict_hostkey_check' in kwargs else False

    def verify(self):
        if self.branch_name == '':
            return 'No project branch specified!'

        if self.repo_name == '':
            return 'Git repo not specified!'

        if self.output_folder == '':
            return 'No output folder specified!'

        return ''

    def run(self):
        # First make sure we actually have git credentials
        ssh_path = os.path.join(os.environ['USERPROFILE'], '.ssh')
        if not os.path.exists(ssh_path) and self.rsa_path != '':
            rsa_file = os.path.join(self.config.uproject_dir_path, self.rsa_path)
            if not os.path.isfile(rsa_file):
                self.error = 'No git credentials exists at rsa_path! ' \
                             'Check rsa_path is relative to the project path and exists.'
                return False
            os.mkdir(ssh_path)
            shutil.copy2(rsa_file, ssh_path)

        # To get around the annoying user prompt, lets just set github to be trusted, no key checking
        if self.disable_strict_hostkey_check:
            if not os.path.isfile(os.path.join(ssh_path, 'config')):
                with open(os.path.join(ssh_path, 'config'), 'w') as fp:
                    fp.write('Host github.com\nStrictHostKeyChecking no')

        output_dir = os.path.join(self.config.uproject_dir_path, self.output_folder)

        if self.force_repull and os.path.exists(output_dir):
            print_action("Deleting Unreal Engine Folder for a complete re-pull")

            def on_rm_error(func, path, exc_info):
                # path contains the path of the file that couldn't be removed
                # let's just assume that it's read-only and unlink it.
                del func  # unused
                if exc_info[0] is not FileNotFoundError:
                    os.chmod(path, stat.S_IWRITE)
                    os.unlink(path)

            # Forcing a re-pull, delete the whole engine directory!
            shutil.rmtree(output_dir, onerror=on_rm_error)

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        if not os.path.isdir(os.path.join(output_dir, '.git')):
            print_action("Cloning from Git '{}' branch '{}'".format(self.repo_name, self.branch_name))
            cmd_args = ['clone', '-b', self.branch_name, self.repo_name, output_dir]
            err = launch('git', cmd_args)
            if err != 0:
                self.error = 'Git clone failed!'
                return False
        else:
            with push_directory(output_dir):
                print_action("Pulling from Git '{}' branch '{}'".format(self.repo_name, self.branch_name))
                err = launch('git', ['pull', 'origin', self.branch_name], silent=True)
                if err != 0:
                    self.error = 'Git pull failed!'
                    return False
        return True
