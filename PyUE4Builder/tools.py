#!/usr/bin/env python

import os
import sys
import click
import json
import time
import shutil
import subprocess
from utility.common import launch, print_action, get_visual_studio_version, error_exit, push_directory
from config import ProjectConfig
from copy import deepcopy

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer", "VREAL"]


pass_config = click.make_pass_decorator(ProjectConfig, ensure=True)
script_file_path = ''


@click.group()
@click.option('--ensure_engine/--ignore_engine',
              default=True,
              show_default=True,
              help='Should the engine exist to be able to run this tool command?')
@click.option('--script', '-s',
              type=click.STRING,
              required=True,
              help='The Project Script which defines the projects paths, build steps, and extra information.')
@pass_config
def tools(config: ProjectConfig, script, ensure_engine):
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
        if not config.load_configuration(script_json, ensure_engine=ensure_engine):
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
                '-game',
                '-engine']
    if config.engine_major_version == 4 and config.engine_minor_version <= 25:
        cmd_args.append('-VS{}'.format(get_visual_studio_version(config.get_suitable_vs_versions())))

    if launch(config.UE4UBTPath, cmd_args) != 0:
        error_exit('Failed to generate project files, see errors...', not config.automated)

    if run_it:
        launch(os.path.join(config.uproject_dir_path, config.uproject_name + '.sln'),
               separate_terminal=True,
               should_wait=False)


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
@click.option('--res', '-r',
              type=click.STRING,
              default='1920x1080',
              help='Resolution control of the window')
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
def standalone(config: ProjectConfig, extra, ip, waittime, umap, res):
    """ Run a standalone build of the game """
    standalone_func(config, extra, ip, waittime, umap, res)


def standalone_func(config: ProjectConfig, extra, ip, waittime, umap, res):
    """ Run a standalone build of the game """
    print_action('Running Standalone')
    cmd_args = [config.uproject_file_path,
                '-game',
                '-windowed',
                '-ResX=%s' % res.split('x')[0],
                '-ResY=%s' % res.split('x')[1]]
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
        result = subprocess.run(["p4", "client", "-o"],
                                stdout=subprocess.PIPE,
                                timeout=4,
                                check=False).stdout.decode("utf-8")
        in_error = 'error' in result
    except Exception:
        in_error = True
    if in_error:
        error_exit('A connection could not be made with perforce. Check your settings and try again.',
                   not config.automated)


def fix_redirects(config: ProjectConfig):
    print_action('Fixing Redirectors')
    cmd_args = [config.uproject_file_path,
                '-run=ResavePackages',
                '-fixupredirects',
                '-autocheckout',
                '-projectonly',
                '-unattended']
    if launch(config.UE4EditorPath, cmd_args) != 0:
        error_exit('Failed to fixup redirectors, see errors...', not config.automated)

    if not config.automated:
        click.pause()


def compile_all_blueprints(config: ProjectConfig):
    print_action('Compiling All Blueprints')
    cmd_args = [config.uproject_file_path,
                '-run=CompileAllBlueprints',
                '-autocheckout',
                '-projectonly',
                '-unattended']
    if launch(config.UE4EditorPath, cmd_args) != 0:
        error_exit('Failed to compile all blueprints, see errors...', not config.automated)

    if not config.automated:
        click.pause()


def do_project_build(extra_args=None):
    args = [os.path.join(os.path.dirname(__file__), 'build_script.py'),
            '-s', '{}'.format(script_file_path), '-t', 'Editor']
    if extra_args is not None:
        args.extend(extra_args)
    result = launch(os.path.join(os.environ.get("PYTHON_HOME", ".").replace('"', ''), "python.exe"),
                    args,
                    False,
                    should_wait=True)
    return result == 0


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
                          "9: Setup Perforce Credentials\n"
                          "10: Fixup Redirectors\n"
                          "11: Compile All Blueprints\n",
                          type=int)
    if result is None:
        return

    if result == 1:
        runeditor_func(config)
    elif result == 2:
        do_project_build()
    elif result == 3:
        do_project_build(['--clean'])
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
    elif result == 10:
        fix_redirects(config)
    elif result == 11:
        compile_all_blueprints(config)


class ProjectBuildCheck(object):
    repos_to_check = {}
    cache_file_name = 'project_cache.json'
    engine_dir = ''
    engine_branch = ''

    def __init__(self, config: ProjectConfig):
        self.from_file = False
        self.repo_rev = ''
        self.engine_repo_rev = ''
        self.other_repos = {}
        ProjectBuildCheck.populate_check_repos(config)
        self.load_cache()
        ProjectBuildCheck.engine_dir = config.UE4EnginePath
        if 'git_engine_branch' in config.script['config']:
            ProjectBuildCheck.engine_branch = config.script['config']['git_engine_branch']
        else:
            ProjectBuildCheck.engine_branch = config.script['config']['git_proj_branch']

    def load_cache(self):
        try:
            with open(ProjectBuildCheck.cache_file_name, 'r') as fp:
                json_s = json.load(fp)
                for k, v in json_s.items():
                    setattr(self, k, v)
                self.from_file = True
        except IOError:
            pass
        except ValueError:
            pass
        for other_repo in ProjectBuildCheck.repos_to_check.keys():
            if other_repo not in self.other_repos:
                self.other_repos[other_repo] = ''

    def update_repo_rev_cache(self):
        with push_directory(ProjectBuildCheck.engine_dir, False):
            self.engine_repo_rev = ProjectBuildCheck.get_cwd_repo_rev(ProjectBuildCheck.engine_branch)
        if os.path.exists('.git'):
            self.repo_rev = ProjectBuildCheck.get_cwd_repo_rev('master')
        for to_dir, branch in ProjectBuildCheck.repos_to_check.items():
            with push_directory(os.path.join(os.getcwd(), to_dir), False):
                self.other_repos[to_dir] = ProjectBuildCheck.get_cwd_repo_rev(branch)

    def save_cache(self):
        with open(ProjectBuildCheck.cache_file_name, 'w') as fp:
            out = deepcopy(self.__dict__)
            del out['from_file']
            json.dump(out, fp, indent=4)

    def was_loaded(self):
        return self.from_file

    @staticmethod
    def get_cwd_repo_rev(branch_name):
        subprocess.check_output(["git", "fetch"])
        return subprocess.check_output(["git", "rev-parse", "--short", branch_name]).decode("utf-8").strip()

    @staticmethod
    def get_cwd_repo_status():
        return subprocess.check_output(["git", "status"]).decode("utf-8")

    @staticmethod
    def get_cwd_branch_name():
        branches = subprocess.check_output(["git", "branch"]).decode("utf-8").splitlines()
        for branch in branches:
            if branch.strip().startswith('*'):
                return branch.replace('*', '', 1).strip()
        return ''

    @staticmethod
    def populate_check_repos(config: ProjectConfig):
        for step in config.script['pre_build_steps']:
            if step['action']['module'] == 'actions.git':
                ProjectBuildCheck.repos_to_check['{}\\{}'.format(config.uproject_name,
                                                                 step['action']['args']['output_folder'])] = \
                    step['action']['args']['branch']

    def check_repos(self):
        # Check the engine repo
        if not os.path.isdir(ProjectBuildCheck.engine_dir):
            return False
        with push_directory(ProjectBuildCheck.engine_dir, False):
            if self.get_cwd_branch_name() != self.engine_branch:
                return False
            if self.engine_repo_rev != self.get_cwd_repo_rev('origin/{}'.format(self.engine_branch)):
                return False
        # Check the local repo against our cached value
        if os.path.exists('.git'):
            if self.repo_rev != self.get_cwd_repo_rev('origin/master'):
                return False
        for to_dir, branch in ProjectBuildCheck.repos_to_check.items():
            if not os.path.isdir(os.path.join(os.getcwd(), to_dir)):
                return False
            with push_directory(os.path.join(os.getcwd(), to_dir), False):
                if self.get_cwd_branch_name() != branch:
                    return False
                if self.other_repos[to_dir] != self.get_cwd_repo_rev('origin/{}'.format(branch)):
                    return False
        return True

    fetch_result_OOD = '- out of date -'
    fetch_result_commit = '- can commit -'
    fetch_result_none = ''

    def fetch_status_info_result(self, repo_name, cur_rev, other_rev):
        info_out = ''
        result = self.fetch_result_none
        if cur_rev != other_rev:
            info_out += 'out-of_date'
            result = self.fetch_result_OOD
        status = self.get_cwd_repo_status()
        if 'nothing to commit, working tree clean' not in status:
            status = status.split('\n')
            info_out += '{}Needs commit:\n'.format('' if len(info_out) == 0 else ' - ')
            for stat in status[5:]:
                if len(stat) != 0 and '(' not in stat:
                    info_out += (stat + '\n')
            result = self.fetch_result_commit
        if len(info_out) != 0:
            print('{} : {}'.format(repo_name, info_out))
        else:
            print('{} up-to-date!'.format(repo_name))
        return result

    @staticmethod
    def ask_do_commit():
        ask_do_commit = click.confirm('Make Commit?', default=False)
        if ask_do_commit:
            git_filter = click.prompt('Type optional filter', default='*')
            message = click.prompt('Type commit message (split on \\n)')
            messages = message.split('\\n')
            git_cmd = ["git", "commit"]
            for message in messages:
                git_cmd.append('-m')
                git_cmd.append('- {}'.format(message.strip()))
            print(subprocess.check_output(["git", "add", git_filter]).decode("utf-8"))
            print(subprocess.check_output(["git", "status"]).decode("utf-8"))
            if click.confirm('All Good?', default=False):
                print(subprocess.check_output(git_cmd).decode("utf-8"))
                print(subprocess.check_output(["git", "push"]).decode("utf-8"))
                return True
            else:
                print('Skipping so you can fix...')
        return False

    def check_and_print_repo_status(self):
        cache_updated = False
        ask_about_commits = click.confirm('Would you like to make commits?', default=False)
        # Check the engine repo
        with push_directory(ProjectBuildCheck.engine_dir, False):
            engine_rev = ProjectBuildCheck.get_cwd_repo_rev('origin/{}'.format(ProjectBuildCheck.engine_branch))
            self.fetch_status_info_result('Engine', self.engine_repo_rev, engine_rev)
        # Check the local repo against our cached value
        if os.path.exists('.git'):
            result = self.fetch_status_info_result('Project', self.repo_rev,
                                                   ProjectBuildCheck.get_cwd_repo_rev('origin/master'))
            if ask_about_commits:
                if result == self.fetch_result_commit:
                    if self.ask_do_commit():
                        self.repo_rev = ProjectBuildCheck.get_cwd_repo_rev('origin/master')
                        cache_updated = True
                elif result == self.fetch_result_OOD:
                    if click.confirm('Update cached rev?', default=False):
                        self.repo_rev = ProjectBuildCheck.get_cwd_repo_rev('origin/master')
                        cache_updated = True
        for to_dir, branch in ProjectBuildCheck.repos_to_check.items():
            if not os.path.isdir(os.path.join(os.getcwd(), to_dir)):
                print('"{}" sub repo doesn\'t exist!'.format(to_dir))
            with push_directory(os.path.join(os.getcwd(), to_dir), False):
                path_splits = os.path.split(to_dir)
                branch_path = 'origin/{}'.format(branch)
                result = self.fetch_status_info_result(path_splits[len(path_splits) - 1].title(),
                                                       self.other_repos[to_dir],
                                                       ProjectBuildCheck.get_cwd_repo_rev(branch_path))
                if ask_about_commits:
                    if result == self.fetch_result_commit:
                        if self.ask_do_commit():
                            self.other_repos[to_dir] = ProjectBuildCheck.get_cwd_repo_rev(branch_path)
                            cache_updated = True
                    elif result == self.fetch_result_OOD:
                        if click.confirm('Update cached rev?', default=False):
                            self.other_repos[to_dir] = ProjectBuildCheck.get_cwd_repo_rev(branch_path)
                            cache_updated = True
        if cache_updated:
            self.save_cache()


@tools.command()
@pass_config
def build_project_if_changed(config: ProjectConfig):
    print_action('Checking Project Build Status...')
    build_checker = ProjectBuildCheck(config)
    if not build_checker.check_repos():
        if not do_project_build(['--error_pause_only']):
            sys.exit(1)
        else:
            build_checker.update_repo_rev_cache()
            build_checker.save_cache()


@tools.command()
@pass_config
def build_project_if_first_sync(config: ProjectConfig):
    if config.UE4EnginePath == '':
        # No engine, definitely build project
        print_action('No engine found, running full build...')
        if not do_project_build(['--error_pause_only']):
            sys.exit(1)
        else:
            config.setup_engine_paths()
            build_checker = ProjectBuildCheck(config)
            build_checker.update_repo_rev_cache()
            build_checker.save_cache()
    else:
        print_action('Checking First Sync Status...')
        build_checker = ProjectBuildCheck(config)
        if not build_checker.was_loaded():
            # First sync, so do a build
            if not do_project_build(['--error_pause_only']):
                sys.exit(1)
            else:
                build_checker.update_repo_rev_cache()
                build_checker.save_cache()


@tools.command()
@pass_config
def report_repo_status(config: ProjectConfig):
    print_action('Repo Status:')
    build_checker = ProjectBuildCheck(config)
    build_checker.check_and_print_repo_status()


# def main_test():
#     message = click.prompt('Type commit message')
#     messages = message.split('\\n')
#     git_cmd = ["git", "commit"]
#     for message in messages:
#         git_cmd.append('-m')
#         git_cmd.append('"- {}"'.format(message.strip()))
#     print(git_cmd)


if __name__ == "__main__":
    try:
        tools()
    except Exception as e:
        error_exit('{}'.format(e), False)
