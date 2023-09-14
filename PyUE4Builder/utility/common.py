#!/usr/bin/env python

import os
import winreg
import click
import sys
import subprocess
import platform
from contextlib import contextmanager
from winregistry import WinRegistry as Reg

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
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
    click.secho('\n{0}\n'.format(msg), bg='yellow', fg='white')


def print_error(msg):
    """
    Print an error message to console
    :param msg: The error message to print
    """
    click.secho('\n{0}\n'.format(msg), bg='red')


def error_exit(msg, should_pause):
    print_error(msg)
    if should_pause:
        click.pause()
    sys.exit(1)


@contextmanager
def push_directory(dir_name, print_steps=True):
    """
    Push a directory as the current working directory. Yield until finished.
    :param dir_name: Directory Name
    :param print_steps: Print the pushing and popping of this routine
    """
    if print_steps:
        click.secho('Pushing {}'.format(dir_name))
    old_dir = os.getcwd()
    os.chdir(dir_name)
    yield
    if print_steps:
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
    if os.path.isdir(dir_path):
        # UE 4 Check
        if os.path.isfile(os.path.join(dir_path, 'Engine/Binaries/DotNET/GitDependencies.exe')):
            return True
        # UE 5 Check
        if os.path.isfile(os.path.join(dir_path, 'Engine/Binaries/DotNET/GitDependencies/win-x64/GitDependencies.exe')):
            return True
    return False


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


def get_visual_studio_version(supported_versions=None):
    """
    Determines the current version of visual studio usable by the unreal engine using registery key lookups.
    Returns the highest compatible version, e.g. will return 2017 if 2015 and 2017 are both installed.
    @param supported_versions: Can be None. An array of versions which can be returned.
    :return: An integer representing the version by year. e.g. 15.0 will return 2017.
             If no version is found, returns -1.
    """
    versions_found = set()
    highest_version = -1
    try:
        # First try for 2015 to 2017
        try:
            hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\VisualStudio\\SxS\\VS7")
            try:
                winreg.QueryValueEx(hkey, '15.0')
                versions_found.add(2017)
                if highest_version == -1:
                    highest_version = 2017
            except FileNotFoundError:
                pass
            try:
                winreg.QueryValueEx(hkey, '14.0')
                versions_found.add(2015)
                if highest_version == -1:
                    highest_version = 2015
            except FileNotFoundError:
                pass
            hkey.Close()
        except FileNotFoundError:
            pass
        # Now try for 2019
        try:
            hkey2019 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\VisualStudio\\16.0")
            versions_found.add(2019)
            highest_version = 2019
            hkey2019.Close()
        except FileNotFoundError:
            pass
        # Now try for 2022
        try:
            hkey2022 = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\WOW6432Node\\Microsoft\\VisualStudio\\17.0")
            versions_found.add(2022)
            highest_version = 2022
            hkey2022.Close()
        except FileNotFoundError:
            pass
    except OSError:
        return -1

    if len(versions_found) == 0:
        return -1

    if supported_versions is None or len(supported_versions) == 0:
        return highest_version

    supported = set(supported_versions)
    allowed_versions = supported.intersection(versions_found)
    version_out = -1
    for version_check in allowed_versions:
        if version_check > version_out:
            version_out = version_check

    return version_out


def register_project_engine(config, prompt_path=True):
    """
    Register the projects engine
    :return: True on success
    """
    reg = Reg()
    # try:
    #     registered_engines = reg.read_key(config.UE4EngineBuildsReg)['values']
    #     for engine in registered_engines:
    #         eng_val = engine['value']  # type:str
    #         if eng_val.startswith('{') and eng_val.endswith('}'):
    #             click.secho("Removing arbitrary Engine Association {0}".format(eng_val))
    #             reg.delete_value(config.UE4EngineBuildsReg, engine['value'])
    # except Exception:
    #     # No entries yet, all good!
    #     pass

    if check_engine_dir_valid(config.UE4EnginePath):
        # Check if the engine is already registered
        try:
            registered_engines = reg.read_key(config.UE4EngineBuildsReg)['values']
            for engine in registered_engines:
                if engine['value'] == config.UE4EngineKeyName:
                    # Check if the data matches the engine path, if not, update the key
                    if engine['data'] != config.UE4EnginePath:
                        click.secho('Updating engine registry key {0}:{1} to {2}'.format(config.UE4EngineKeyName,
                                                                                         engine['data'],
                                                                                         config.UE4EnginePath))
                        click.secho('This is probably because the engine has been moved.')
                        reg.write_value(config.UE4EngineBuildsReg,
                                        config.UE4EngineKeyName,
                                        config.UE4EnginePath,
                                        'REG_SZ')
                    return True
        except Exception:
            pass

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
        print_error("Could not find engine path to register!")
        return False
    return True


def do_ms_build(proj_path):
    ms_build_tool = os.path.expandvars('%ProgramFiles(x86)%\\MSBuild\\14.0\\bin\\MSBuild.exe')
    cmd_str = '{} /nologo /verbosity:quiet {} ' \
              '/property:Configuration=Development /property:Platform=AnyCPU /target:Build'.format(ms_build_tool,
                                                                                                   proj_path)
    if os.system(cmd_str) != 0:
        print_error('Failed to build MS Build project {}'.format(proj_path))
