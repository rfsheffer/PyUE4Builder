#!/usr/bin/env python

from actions.action import Action
import os
import stat
import shutil

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer"]


class Delete(Action):
    """
    Delete Action
    An action designed to delete files/folders as part of a build process.
    """
    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.paths = kwargs['paths'] if 'paths' in kwargs else []
        self.verify_exist = kwargs['verify_exist'] if 'verify_exist' in kwargs else False

    def verify(self):
        if not len(self.paths):
            return 'No deletion paths specified!'
        updated_paths = []
        for file_path in self.paths:
            file_path = self.replace_tags(file_path)

            if self.verify_exist and (not os.path.isdir(file_path) or not os.path.isfile(file_path)):
                return 'Invalid deletion path specified : "{}"'.format(file_path)
            updated_paths.append(file_path)
        self.paths = updated_paths
        return ''

    def run(self):
        for file_path in self.paths:
            if os.path.isdir(file_path):
                def on_rm_error(func, path, exc_info):
                        # path contains the path of the file that couldn't be removed
                        # let's just assume that it's read-only and unlink it.
                        del func  # unused
                        if exc_info[0] is not FileNotFoundError:
                            os.chmod(path, stat.S_IWRITE)
                            os.unlink(path)

                try:
                    shutil.rmtree(file_path, onerror=on_rm_error)
                except Exception as e:
                    self.error = 'Unable to delete the directory: {}. Error: {}. ' \
                                 'Check that the files in the folder are not open / held by another process and try again.'.format(file_path, str(e))
                    return False
            elif os.path.isfile(file_path):
                try:
                    os.unlink(file_path)
                except Exception:
                    os.chmod(file_path, stat.S_IWRITE)
                    os.unlink(file_path)
        return True
