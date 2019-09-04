#!/usr/bin/env python

import os
import click
import json
import time
import shutil
import subprocess
from utility.common import launch, print_action, get_visual_studio_version, error_exit
from config import ProjectConfig

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


pass_config = click.make_pass_decorator(ProjectConfig, ensure=True)
script_file_path = ''


@click.group()
@click.option('--script', '-s',
              type=click.STRING,
              required=True,
              help='The Project Script which defines the projects paths, build steps, and extra information.')
@pass_config
def tools(config: ProjectConfig, script):
    if not os.path.isfile(script):
        error_exit('No build script defined! Use the -s arg', not config.automated)

    global script_file_path
    script_file_path = script
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
    genproj_func(config, False)


@tools.command()
@pass_config
def genproj_run(config: ProjectConfig):
    """ Generate project file """
    genproj_func(config, True)


def genproj_func(config: ProjectConfig, run_it):
    """ Generate project file """
    print_action('Generating Project Files')

    cmd_args = ['-ProjectFiles',
                '-project={}'.format(config.uproject_file_path),
                '-game', '-engine']
    if get_visual_studio_version() == 2017:
        cmd_args.append('-2017')
    if launch(config.UE4UBTPath, cmd_args) != 0:
        error_exit('Failed to generate project files, see errors...', not config.automated)

    if run_it:
        pass


@tools.command()
@pass_config
def genloc(config: ProjectConfig):
    """ Generate localization """
    genloc_func(config)


def genloc_func(config: ProjectConfig):
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
def standalone(config: ProjectConfig, extra, ip, waittime, umap):
    """ Run a standalone build of the game """
    standalone_func(config, extra, ip, waittime, umap)


def standalone_func(config: ProjectConfig, extra, ip, waittime, umap):
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
def server(config: ProjectConfig, extra, umap):
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
def client(config: ProjectConfig, extra, ip):
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
def runeditor(config: ProjectConfig):
    """ Run the editor with the registered project """
    runeditor_func(config)


def runeditor_func(config: ProjectConfig):
    """ Run the editor with the registered project """
    print_action('Running Editor')
    launch(config.UE4EditorPath, [config.uproject_file_path], True, should_wait=False)


def setup_perforce_creds(config: ProjectConfig):
    if shutil.which("p4") is None:
        error_exit('Perforce was not found on the path. Make sure perforce is installed and on your systems path.',
                   not config.automated)

    if os.path.isfile('p4config.txt'):
        result = click.confirm('Credentials already set. Overwrite them?', default=False)
        if not result:
            return

    with open('p4config.txt', 'w') as p4_file:
        user_name = click.prompt('Type User Name')
        if user_name is None:
            return

        client_name = click.prompt('Type Workspace Name')
        if client_name is None:
            return

        server_name = click.prompt('Type Server Address ex: ssl:127.0.0.1:1666')
        if server_name is None:
            return

        p4_file.writelines(['P4USER={}\n'.format(user_name),
                            'P4CLIENT={}\n'.format(client_name),
                            'P4PORT={}'.format(server_name)])

    try:
        subprocess.check_output(["p4", "set", "P4CONFIG=p4config.txt"])
        result = subprocess.run(["p4", "client", "-o"], stdout=subprocess.PIPE, timeout=4, check=False).stdout.decode("utf-8")
        in_error = 'error' in result
    except Exception:
        in_error = True
    if in_error:
        error_exit('A connection could not be made with perforce. Check your settings and try again.',
                   not config.automated)


@tools.command()
@pass_config
def tools_select(config: ProjectConfig):
    """ Opens a utilities/tools selection prompt """
    result = click.prompt("Project Tools (Select Option):\n"
                          "1: Run Editor\n"
                          "2: Build Project\n"
                          "3: Build Project (Clean)\n"
                          "4: Run Standalone\n"
                          "5: Generate Project Files\n"
                          "6: Generate Localization\n"
                          "7: Run Editor (No Sync Check)\n"
                          "8: Run Visual Studio\n"
                          "9: Setup Perforce Credentials\n", type=int)
    if result is None:
        return

    if result == 1:
        runeditor_func(config)
    elif result == 2:
        launch(os.path.join(os.environ.get("PYTHON_HOME", "."), "python.exe"),
               ['build_script.py', '-s "{}"'.format(script_file_path), '-t Editor'], True, should_wait=False)
    elif result == 3:
        launch(os.path.join(os.environ.get("PYTHON_HOME", "."), "python.exe"),
               ['build_script.py', '-s "{}"'.format(script_file_path), '-t Editor', '--clean'], True, should_wait=False)
    elif result == 4:
        standalone_func(config, '', '', 0, '')
    elif result == 5:
        genproj_func(config, False)
    elif result == 6:
        genloc_func(config)
    elif result == 7:
        runeditor_func(config)
    elif result == 8:
        genproj_func(config, True)
    elif result == 9:
        setup_perforce_creds(config)

if __name__ == "__main__":
    try:
        tools()
    except Exception as e:
        error_exit('{}'.format(e), False)
