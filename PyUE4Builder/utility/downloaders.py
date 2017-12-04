#!/usr/bin/env python

import os
from urllib.request import urlopen

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


def download_file(file_url, output_folder='.', simple_loading=False):
    """
    Download a file and show a fancy output
    :param file_url: The URL of the file to download
    :param output_folder: The folder to output to, defaults to current working directory
    :param simple_loading: Should the loading output have no animation?
    """
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)
    file_name = file_url.split('/')[-1]
    u = urlopen(file_url)
    file_name_out = os.path.join(output_folder, file_name)
    if os.path.isfile(file_name_out):
        os.unlink(file_name_out)
    with open(file_name_out, 'wb') as fp:
        file_size = int(dict(u.info())["Content-Length"])
        print("Downloading: {} Bytes: {}".format(file_name, file_size))

        file_size_dl = 0
        block_sz = 8192
        simple_loading_sz = 524288
        cur_simple_loading = 0
        while True:
            buff = u.read(block_sz)
            if not buff:
                break

            file_size_dl += len(buff)
            fp.write(buff)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100.0 / file_size)
            if simple_loading:
                if file_size_dl > cur_simple_loading or file_size_dl >= file_size:
                    cur_simple_loading += simple_loading_sz
                    print(status, flush=True)
            else:
                # Clear the previous page before printing, add the required number of backspaces
                # NOTE: This works in the terminal, rarely works in a UI text field pulling characters from the stream
                status += chr(8) * len(status)
                print(status, end='', flush=True)
    print('')
