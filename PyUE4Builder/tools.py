#!/usr/bin/env python

import os
import click
import json
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
        error_exit('No build script defined! Use the -s arg')

    with open(script, 'r') as fp:
        script_json = json.load(fp)
        if not config.load_configuration(script_json, ensure_engine=True):
            error_exit('Invalid Script file!')


@tools.command()
@pass_config
def genproj(config):
    """ Generate project file """
    print_action('Generating Project Files')

    # extra_args = ''
    # if get_visual_studio_version() == 2017:
    #     extra_args += '-2017'
    #
    # ubt_cmd = '{0} -ProjectFiles -project={1} -game -engine {2}'.format(config.UE4UBTPath,
    #                                                                     config.uproject_file_path,
    #                                                                     extra_args)
    cmd_args = ['-ProjectFiles',
                '-project={}'.format(config.uproject_file_path),
                '-game', '-engine']
    if get_visual_studio_version() == 2017:
        cmd_args.append('-2017')
    if launch(config.UE4UBTPath, cmd_args) != 0:
        error_exit('Failed to generate project files, see errors...')


@tools.command()
@pass_config
def genloc(config):
    """ Generate localization """
    print_action('Generating Localization')
    # cmd_str = '{0} {1} -Run=GatherText -config={2} -log'.format(config.UE4EditorPath,
    #                                                             config.uproject_file_path,
    #                                                             config.proj_localization_script)
    cmd_args = [config.uproject_file_path,
                '-Run=GatherText',
                '-config={}'.format(config.proj_localization_script),
                '-log']
    if launch(config.UE4EditorPath, cmd_args) != 0:
        error_exit('Failed to generate localization, see errors...')

    click.pause()


@tools.command()
@pass_config
def standalone(config):
    """ Run a standalone build of the game """
    print_action('Running Standalone')
    # cmd_str = '{0} {1} -game -windowed -ResX=1280 -ResY=720'.format(config.UE4EditorPath,
    #                                                                 config.uproject_file_path)
    cmd_args = [config.uproject_file_path,
                '-game',
                '-windowed',
                '-ResX=1280',
                '-ResY=720']
    launch(config.UE4EditorPath, cmd_args, True, should_wait=False)


@tools.command()
@pass_config
def runeditor(config):
    """ Run the editor with the registered project """
    print_action('Running Editor')
    # cmd_str = '{0} {1}'.format(config.UE4EditorPath, config.uproject_file_path)
    launch(config.UE4EditorPath, [config.uproject_file_path], True, should_wait=False)


if __name__ == "__main__":
    try:
        tools()
    except Exception as e:
        error_exit('{}'.format(e))
