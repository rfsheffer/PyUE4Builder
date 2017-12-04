#!/usr/bin/env python

import json
from copy import deepcopy


class BuildMeta(object):
    """
    This class contains saved meta data about the build process.
    Store information which is helpful for builds or future builds.
    """
    def __init__(self, meta_file_name):
        self.meta_file_name = meta_file_name
        self.load_meta()

    def load_meta(self):
        try:
            with open('{}.json'.format(self.meta_file_name), 'r') as fp:
                json_s = json.load(fp)
                for k, v in json_s.items():
                    setattr(self, k, v)
        except IOError:
            pass
        except ValueError:
            pass

    def save_meta(self):
        with open('{}.json'.format(self.meta_file_name), 'w') as fp:
            json.dump(self.__dict__, fp, indent=4)

    def collect_meta(self, meta_fields):
        """
        Collect meta data into a dictionary
        :param meta_fields: The fields to collect in a list
        :return: A dict of meta fields
        """
        args_out = {}
        for field in meta_fields:
            attr = getattr(self, field, None)
            if attr is not None:
                args_out[field] = deepcopy(attr)
        return args_out

    def insert_meta(self, overwrite=False, **kwargs):
        for k, w in kwargs.items():
            if not getattr(self, k, None) or overwrite:
                setattr(self, k, deepcopy(w))
