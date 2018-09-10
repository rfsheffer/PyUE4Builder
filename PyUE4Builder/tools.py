#!/usr/bin/env python

import os
import click
import json
import time
from utility.common import launch, print_action, get_visual_studio_version, error_exit
from config import ProjectConfig

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


pass_config = click.make_pass_decorator(ProjectConfig, ensure=True)


@click.group()
@click.option('--script', '-s',
              type=click.STRING,
              required=True,
              help='The Project Script which defines the projects paths, build steps, and extra information.')
@pass_config
def tools(config: ProjectConfig, script):
    if not os.path.isfile(script):
        error_exit('No build script defined! Use the -s arg', not config.automated)

    with open(script, 'r') as fp:
        try:
            script_json = json.load(fp)
        except Exception as jsonError:
            error_exit('Build Script Syntax Error:\n{}'.format(jsonError), not config.automated)
            return
        if not config.load_configuration(script_json, ensure_engine=True):
            error_exit('Invalid Script file!', not config.automated)


@tools.command()
@pass_config
def genproj(config: ProjectConfig):
    """ Generate project file """
    print_action('Generating Project Files')

    cmd_args = ['-ProjectFiles',
                '-project={}'.format(config.uproject_file_path),
                '-game', '-engine']
    if get_visual_studio_version() == 2017:
        cmd_args.append('-2017')
    if launch(config.UE4UBTPath, cmd_args) != 0:
        error_exit('Failed to generate project files, see errors...', not config.automated)


@tools.command()
@pass_config
def genloc(config: ProjectConfig):
    """ Generate localization """
    print_action('Generating Localization')
    cmd_args = [config.uproject_file_path,
                '-Run=GatherText',
                '-config={}'.format(config.proj_localization_script),
                '-log']
    if launch(config.UE4EditorPath, cmd_args) != 0:
        error_exit('Failed to generate localization, see errors...', not config.automated)

    if not config.automated:
        click.pause()


@tools.command()
@click.option('--umap', '-m',
              type=click.STRING,
              default='',
              help='The map to load')
@click.option('--waittime', '-w',
              type=click.INT,
              default=0,
              help='Wait time in seconds before trying to connect to the server IP')
@click.option('--ip', '-i',
              type=click.STRING,
              default='',
              help='IP to connect to as a client')
@click.option('--extra', '-e',
              type=click.STRING,
              default='',
              help='Extra parameters to pass to the game')
@pass_config
def standalone(config, extra, ip, waittime, umap):
    """ Run a standalone build of the game """
    print_action('Running Standalone')
    cmd_args = [config.uproject_file_path,
                '-game',
                '-windowed',
                '-ResX=1280',
                '-ResY=720']
    cmd_args.extend(['-'+arg.strip() for arg in extra.split('-')[1:]])

    if ip != '':
        time.sleep(waittime)
        cmd_args.insert(1, ip)

    if umap != '':
        cmd_args.insert(1, umap)

    launch(config.UE4EditorPath, cmd_args, True, should_wait=False)


@tools.command()
@click.option('--umap', '-m',
              type=click.STRING,
              default='',
              help='The map to load')
@click.option('--extra', '-e',
              type=click.STRING,
              default='',
              help='Extra parameters to pass to the game')
@pass_config
def server(config, extra, umap):
    """ Run a server """
    print_action('Running Server')
    cmd_args = []
    cmd_args.extend(['-' + arg.strip() for arg in extra.split('-')[1:]])

    if umap != '':
        cmd_args.insert(0, umap)

    server_exe_path = os.path.join(config.uproject_dir_path,
                                   'builds\\WindowsServer\\{0}\\Binaries\\'
                                   'Win64\\{0}Server.exe'.format(config.uproject_name))
    if not os.path.isfile(server_exe_path):
        error_exit('Server is not built!', not config.automated)

    launch(server_exe_path, cmd_args, True, should_wait=False)


@tools.command()
@click.option('--ip', '-i',
              type=click.STRING,
              default='',
              help='IP to connect to as a client')
@click.option('--extra', '-e',
              type=click.STRING,
              default='',
              help='Extra parameters to pass to the game')
@pass_config
def client(config, extra, ip):
    """ Run the client """
    print_action('Running Client')
    cmd_args = ['-game',
                '-windowed',
                '-ResX=1280',
                '-ResY=720']
    cmd_args.extend(['-' + arg.strip() for arg in extra.split('-')[1:]])

    if ip != '':
        cmd_args.insert(0, ip)

    client_exe_path = os.path.join(config.uproject_dir_path,
                                   'builds\\WindowsNoEditor\\{0}\\Binaries\\'
                                   'Win64\\{0}.exe'.format(config.uproject_name))
    if not os.path.isfile(client_exe_path):
        error_exit('Client is not built!', not config.automated)

    launch(client_exe_path, cmd_args, True, should_wait=False)


@tools.command()
@pass_config
def runeditor(config):
    """ Run the editor with the registered project """
    print_action('Running Editor')
    launch(config.UE4EditorPath, [config.uproject_file_path], True, should_wait=False)


if __name__ == "__main__":
    try:
        tools()
    except Exception as e:
        error_exit('{}'.format(e), False)
