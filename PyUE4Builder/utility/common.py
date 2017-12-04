#!/usr/bin/env python

import os
import stat
import winreg
import shutil
import click
import sys
import subprocess
import platform
from contextlib import contextmanager
from winregistry import WinRegistry as Reg

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


def launch(cmd, args=None, separate_terminal=False, in_color='cyan', silent=False, should_wait=True):
    """
    Launch a system command
    :param cmd: The command to run
    :param args: The arguments to pass to that command (a str list)
    :param separate_terminal: Should we open a new terminal window
    :param in_color: The color to output
    :param silent: Echo the system command to the current stdout?
    :param should_wait: In the case of a separate terminal, should we wait for that to finish?
    :return: The error code returned from the command. If not wait to complete, this will only return 0.
    """
    if args is None:
        args = []

    args_in = [cmd]
    if separate_terminal or not should_wait:
        pre_args = ['start']
        if should_wait:
            pre_args.append('/wait')
        pre_args.append(cmd)
        pre_args.extend(args)
        args_in = pre_args
    else:
        args_in.extend(args)

    if not silent:
        click.secho(' '.join(args_in), fg=in_color)

    return subprocess.call(args_in, shell=separate_terminal or not should_wait)


def print_title(msg):
    """
    Print title
    :param msg: The title to print
    """
    click.secho('\n\n{0}\n'.format(msg), bg='blue', fg='yellow', nl=False, bold=True)


def print_heading(msg):
    """
    Print header for logging
    :param msg: The message to print in the header
    """
    click.secho('\n{0}\n'.format(msg), bg='cyan')


def print_action(msg):
    """
    Print action, ex. "Running UAT"
    :param msg: The action message
    """
    click.secho('\n{0}\n'.format(msg), bg='green')


def print_action_info(msg):
    """
    Print action info, ex. "UAT is here!"
    :param msg: The action info message
    """
    click.secho('\t{0}\n'.format(msg), bg='green')


def print_warning(msg):
    """
    Print an error message to console
    :param msg: The error message to print
    """
    click.secho('\n{0}\n'.format(msg), bg='yellow', fg='black')


def print_error(msg):
    """
    Print an error message to console
    :param msg: The error message to print
    """
    click.secho('\n{0}\n'.format(msg), bg='red')


def error_exit(msg):
    print_error(msg)
    click.pause()
    sys.exit(1)


@contextmanager
def push_directory(dir_name):
    """
    Push a directory as the current working directory. Yield until finished.
    :param dir_name: Directory Name
    """
    click.secho('Pushing {}'.format(dir_name))
    old_dir = os.getcwd()
    os.chdir(dir_name)
    yield
    click.secho('Popping {}'.format(dir_name))
    os.chdir(old_dir)


def is_editor_running(engine_path=''):
    """
    Check if the engine is running
    :param engine_path: If set to non '' will only care about executables under a specific engine path
    :return: True if the engine is running
    """
    if platform.system() != 'Windows':
        raise Exception('is_editor_running designed for windows. Please fix me!')

    for line in subprocess.check_output(['tasklist']).splitlines():
        process_line = bytes.decode(line).split()
        if len(process_line) < 1:
            continue
        if 'ue4editor' in process_line[0].lower():
            if engine_path != '':
                # Only care about a specific engine exe
                exe_name = process_line[0]
                process_paths_cmd = 'wmic process where "name=\'{}\'" get ProcessID, ExecutablePath'.format(exe_name)
                process_paths = subprocess.check_output(process_paths_cmd, universal_newlines=True)
                for exe_path_info in process_paths.splitlines():
                    exe_path_line = exe_path_info.split()
                    if len(exe_path_line) < 1:
                        continue
                    exe_path = exe_path_line[0]
                    if exe_name in exe_path:
                        if os.path.normpath(engine_path) in os.path.normpath(exe_path):
                            return True
            else:
                return True
    return False


def check_engine_dir_valid(dir_path):
    """
    Check that the engine directory would be considered valid. This is a pretty lazy check, just ensuring a folder
    structure exists, and git dependencies could be called.
    :param dir_path: The directory to check for validity
    :return: True if the directory appears to be valid
    """
    return os.path.isdir(dir_path) and \
        os.path.isfile(os.path.join(dir_path, 'Engine/Binaries/DotNET/GitDependencies.exe'))


def get_p4_ticket(p4_password):
    """
    Tries to login to perforce and get a ticket for all commands to follow
    Fails if no ticket could be established
    @param p4_password: The password to get a ticket for.
    :return: The ticket str
    """
    p1 = subprocess.Popen(["echo", p4_password], shell=True, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['p4', 'login', '-p'], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    outs = p2.communicate()
    parts = bytes.decode(outs[0]).split('\r\n')
    return parts[1] if len(parts) == 3 else ''


def get_visual_studio_version():
    """
    Determines the current version of visual studio usable by the unreal engine using registery key lookups.
    Returns the highest compatible version, e.g. will return 2017 if 2015 and 2017 are both installed.
    :return: An integer representing the version by year. e.g. 15.0 will return 2017.
             If no version is found, returns -1.
    """
    try:
        # The most reliable way is to check this install key. The other keys have many variations.
        hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\VisualStudio\\SxS\\VS7")
        try:
            winreg.QueryValueEx(hkey, '15.0')
            hkey.Close()
            return 2017
        except FileNotFoundError:
            pass
        try:
            winreg.QueryValueEx(hkey, '14.0')
            hkey.Close()
            return 2015
        except FileNotFoundError:
            pass
        hkey.Close()
    except OSError:
        pass

    return -1


def register_project_engine(config, prompt_path=True):
    """
    Register the projects engine
    :return: True on success
    """
    reg = Reg()
    try:
        registered_engines = reg.read_key(config.UE4EngineBuildsReg)['values']
        for engine in registered_engines:
            eng_val = engine['value']  # type:str
            if eng_val.startswith('{') and eng_val.endswith('}'):
                click.secho("Removing arbitrary Engine Association {0}".format(eng_val))
                reg.delete_value(config.UE4EngineBuildsReg, engine['value'])
    except Exception:
        # No entries yet, all good!
        pass

    if check_engine_dir_valid(config.UE4EnginePath):
        click.secho('Setting engine registry key {0} to {1}'.format(config.UE4EngineKeyName, config.UE4EnginePath))

        try:
            reg.create_key(config.UE4EngineBuildsReg)
        except Exception:
            pass
        reg.write_value(config.UE4EngineBuildsReg,
                        config.UE4EngineKeyName,
                        config.UE4EnginePath,
                        'REG_SZ')
    elif prompt_path:
        my_engine_path = input('Enter Engine Path: ')
        if check_engine_dir_valid(my_engine_path):
            click.secho('Setting engine registry key {0} to {1}'.format(config.UE4EngineKeyName, my_engine_path))
            reg.write_value(config.UE4EngineBuildsReg,
                            config.UE4EngineKeyName,
                            my_engine_path,
                            'REG_SZ')
        else:
            print_error("Could not find engine path, make sure you type the full path!")
            return False
    else:
        print_error("Could not find engine path!")
        return False
    return True


def pull_git_engine(config, force_repull=False):
    """
    Helper for pulling the unreal engine from git.
    NOTE: For this call to work, you will need to have a git SSH cert in your %USERDIR%/.ssh folder. Also you will
    have to whitelist the cert by running a git command first. Still havn't figured out a way of making this automagic..
    :param config: The current configuration
    :param force_repull: Should the engine be re-pulled? This deletes the engine entirely!
    :return: True if nothing went wrong
    """
    # First make sure we actually have git credentials
    ssh_path = os.path.join(os.environ['USERPROFILE'], '.ssh')
    if not os.path.exists(ssh_path):
        rsa_file = os.path.join(config.uproject_dir_path, 'Scripts\\rsa\\id_rsa')
        if not os.path.isfile(rsa_file):
            print_error('No git credentials exist. You can attain credentials from a project manager!')
            return False
        os.mkdir(ssh_path)
        shutil.copy2(rsa_file, ssh_path)

    # To get around the annoying user prompt, lets just set github to be trusted, no key checking
    if not os.path.isfile(os.path.join(ssh_path, 'config')):
        with open(os.path.join(ssh_path, 'config'), 'w') as fp:
            fp.write('Host github.com\nStrictHostKeyChecking no')

    if force_repull and os.path.exists(config.UE4EnginePath):
        print_action("Deleting Unreal Engine Folder for a complete re-pull")

        def on_rm_error(func, path, exc_info):
            # path contains the path of the file that couldn't be removed
            # let's just assume that it's read-only and unlink it.
            del func  # unused
            if exc_info[0] is not FileNotFoundError:
                os.chmod(path, stat.S_IWRITE)
                os.unlink(path)

        # Forcing a re-pull, delete the whole engine directory!
        shutil.rmtree(config.UE4EnginePath, onerror=on_rm_error)

    if not os.path.isdir(config.UE4EnginePath):
        os.makedirs(config.UE4EnginePath)

    if not os.path.isdir(os.path.join(config.UE4EnginePath, '.git')):
        # Engine not setup, do so!
        print_action("Cloning UnrealEngine from GitHub")
        cmd_args = ['clone', '-b', config.git_proj_branch, config.git_repo, config.UE4EnginePath]
        err = launch('git', cmd_args)
        if err != 0:
            print_error('Git clone failed!')
            return False
    else:
        with push_directory(config.UE4EnginePath):
            print_action("Pulling UnrealEngine from GitHub")
            err = launch('git', ['pull'], silent=True)
            if err != 0:
                print_error('Git pull failed!')
                return False
    return True


def do_ms_build(proj_path):
    ms_build_tool = os.path.expandvars('%ProgramFiles(x86)%\\MSBuild\\14.0\\bin\\MSBuild.exe')
    cmd_str = '{} /nologo /verbosity:quiet {} ' \
              '/property:Configuration=Development /property:Platform=AnyCPU /target:Build'.format(ms_build_tool,
                                                                                                   proj_path)
    if os.system(cmd_str) != 0:
        print_error('Failed to build MS Build project {}'.format(proj_path))
