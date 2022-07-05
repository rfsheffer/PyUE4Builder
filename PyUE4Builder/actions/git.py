#!/usr/bin/env python

from actions.action import Action
import os
import stat
import shutil
import subprocess
from utility.common import print_action, push_directory, launch
import click

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Git(Action):
    """
    Git Action
    An action for syncing a git repo to a specified folder
    """

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.branch_name = kwargs['branch'] if 'branch' in kwargs else ''
        self.similar_branches = kwargs['similar_branches'] if 'similar_branches' in kwargs else ''
        self.repo_name = kwargs['repo'] if 'repo' in kwargs else ''
        self.output_folder = kwargs['output_folder'] if 'output_folder' in kwargs else ''
        self.rsa_path = kwargs['rsa_path'] if 'rsa_path' in kwargs else ''
        self.force_repull = kwargs['force_repull'] if 'force_repull' in kwargs else False
        self.disable_strict_hostkey_check = \
            kwargs['disable_strict_hostkey_check'] if 'disable_strict_hostkey_check' in kwargs else False
        self.branch_switched = False

    def verify(self):
        if self.branch_name == '':
            return 'No project branch specified!'

        if self.repo_name == '':
            return 'Git repo not specified!'

        if self.output_folder == '':
            return 'No output folder specified!'

        return ''

    @staticmethod
    def get_current_branch():
        branches = subprocess.check_output(["git", "branch"]).decode("utf-8").splitlines()
        for branch in branches:
            if branch.strip().startswith('*'):
                return branch.replace('*', '', 1).strip()
        return ''

    def run(self):
        if not self.config.automated:
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

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        elif os.path.isdir(os.path.join(output_dir, '.git')):
            # check if the repo in the folder is on the correct branch. If not, delete the folder so we can
            # start over.
            with push_directory(output_dir, False):
                cur_branch = self.get_current_branch()
                if cur_branch != self.branch_name:
                    if cur_branch in self.similar_branches and self.branch_name in self.similar_branches:
                        do_branch_switch = click.confirm('Branch mismatch but both branches are similar. '
                                                         'Do branch switch? (If you have unsaved changes in this repo '
                                                         'this will clobber them!)')
                        if not do_branch_switch:
                            self.error = 'Clean up your repo manually so a branch switch can be made.'
                            return False
                        err = launch('git', ['fetch', 'origin'])
                        if err != 0:
                            self.error = 'Git fetch failed...'
                            return False
                        # Cleanup before branch switch
                        launch('git', ['checkout', '--', '*'])
                        cmd_args = ['checkout', '-b', self.branch_name, 'origin/{}'.format(self.branch_name)]
                        err = launch('git', cmd_args)
                        if err != 0:
                            ask_do_repull = click.confirm('Tried to switch branches but failed. '
                                                          'Would you like to clobber and re-pull?')
                            if ask_do_repull:
                                self.force_repull = True
                            else:
                                self.error = 'Please correct the issue manually. Check the errors above for hints.'
                                return False
                        else:
                            # Cleanup again just in case
                            launch('git', ['checkout', '--', '*'])
                            self.branch_switched = True
                    else:
                        ask_do_repull = click.confirm('Branch mismatch ("{}" should equal "{}"). Clobber this entire '
                                                      'repo and do a re-pull?'.format(cur_branch,
                                                                                      self.branch_name),
                                                      default=False)
                        if ask_do_repull:
                            self.force_repull = True
                        else:
                            self.error = 'Branch mismatch caused pull to be halted. Please correct the issue manually.'
                            return False

        if self.force_repull:
            print_action("Deleting the folder '{}' for a complete re-pull".format(self.output_folder))

            def on_rm_error(func, path, exc_info):
                # path contains the path of the file that couldn't be removed
                # let's just assume that it's read-only and unlink it.
                del func  # unused
                if exc_info[0] is not FileNotFoundError:
                    os.chmod(path, stat.S_IWRITE)
                    os.unlink(path)

            # Forcing a re-pull, delete the whole directory!
            try:
                shutil.rmtree(output_dir, onerror=on_rm_error)
            except Exception:
                self.error = 'Unable to delete the repo directory for a re-pull. ' \
                             'Check that the files are not open / held by another process and try again.'
                return False
            os.makedirs(output_dir)

        if not os.path.isdir(os.path.join(output_dir, '.git')):
            with push_directory(output_dir, False):
                print_action("Cloning from Git '{}' branch '{}'".format(self.repo_name, self.branch_name))
                def check_launch(cmd, args, err):
                    if launch(cmd, args) != 0:
                        raise Exception(err)
                # We allow git folders to already have content because the binary content might be stored on P4 or other and already be
                # resident in the content folders.
                # The steps below might seem unusual but is the only way to clone into a folder already containing content
                try:
                    check_launch('git', ['init'], 'Failed to init repo!')  # Init git for this folder
                    check_launch('git', ['remote', 'add', 'origin', self.repo_name], 'Failed to add remote!')  # Add the remote to pull from
                    check_launch('git', ['fetch'], 'Failed to fetch from remote!')  # Fetch the remote repo
                    check_launch('git', ['branch', self.branch_name, 'origin/{}'.format(self.branch_name)], 'Failed to create new branch!')  # Create branch from origin
                    check_launch('git', ['checkout', self.branch_name], 'Failed to checkout branch!')  # Checkout branch
                except Exception as e:
                    self.error = e
                    return False
                #cmd_args = ['clone', '-b', self.branch_name, self.repo_name, output_dir]
                #err = launch('git', cmd_args)
                #if err != 0:
                #    self.error = 'Git clone failed!'
                #    return False
        else:
            with push_directory(output_dir, False):
                print_action("Pulling from Git '{}' branch '{}'".format(self.repo_name, self.branch_name))
                err = launch('git', ['pull', 'origin', self.branch_name], silent=True)
                if err != 0:
                    self.error = 'Git pull failed!'
                    return False
        return True

# if __name__ == "__main__":
#     import sys
#
#     class NullConfig:
#         def __init__(self):
#             self.uproject_dir_path = ''
#             self.automated = False
#     git = Git(NullConfig(), output_folder=sys.argv[1], repo=sys.argv[2], branch=sys.argv[3])
#     if not git.run():
#         print(git.error)
