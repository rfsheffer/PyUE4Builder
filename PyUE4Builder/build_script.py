#!/usr/bin/env python

import sys
import os
import click
import json
import importlib
from copy import deepcopy
from build_meta import BuildMeta
from config import ProjectConfig, project_build_types, project_configurations, project_package_types
from utility.common import launch, print_title, print_action, error_exit, print_error, pull_git_engine, \
    get_visual_studio_version, register_project_engine, print_warning, is_editor_running
from actions.build import Build
from actions.package import Package

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


@click.command()
@click.option('--clean', '-c',
              is_flag=True,
              default=False,
              show_default=True,
              help='Clean build? This will leave everything in a cleaned, un-usable state.')
@click.option('--build', '-b',
              type=click.Choice(project_package_types),
              default='Internal',
              show_default=True,
              help='Which build should be created? Only used for packaging.')
@click.option('--buildtype', '-t',
              type=click.Choice(project_build_types),
              default='Game',
              show_default=True,
              help="Which type of build are you trying to create? Game+Editor OR Package?")
@click.option('--configuration', '-c',
              type=click.Choice(project_configurations),
              default='Development',
              show_default=True,
              help="Build configuration, e.g. Shipping")
@click.option('--script', '-s',
              type=click.STRING,
              required=True,
              help='The Project Script which defines the projects paths, build steps, and extra information.')
@click.option('--engine', '-e',
              type=click.STRING,
              default='',
              help='The desired engine path, absolute or relative. Blank will try to find the engine for you.')
def build_script(engine, script, configuration, buildtype, build, clean):
    """
    The Main call for build script execution.
    :param engine: The desired engine path, absolute or relative.
    :param script: The Project Script which defines the projects paths, build steps, and extra information.
    :param configuration: Build configuration, e.g. Shipping
    :param buildtype: Which type of build are you trying to create? Game+Editor OR Package?
    :param build: Which type of build are you trying to create? Game+Editor OR Package?
    :param clean: Clean build? This will leave everything in a cleaned, un-usable state.
    """
    # Ensure Visual Studio is installed
    if get_visual_studio_version() not in [2015, 2017]:
        print_error('Cannot run build, valid visual studio install not found!')
        return False

    if not os.path.isfile(script):
        error_exit('No build script defined! Use the -s arg')

    with open(script, 'r') as fp:
        script_json = json.load(fp)

    config = ProjectConfig(configuration, buildtype, build, clean)
    if not config.load_configuration(script_json, engine, False):
        error_exit('Failed to load configuration. See errors above.')

    print_title('Unreal Project Builder')

    build_meta = BuildMeta('project_build_meta')
    if "meta" in config.script:
        build_meta.insert_meta(**config.script["meta"])

    editor_is_running = is_editor_running(config.UE4EnginePath)

    # Ensure the engine exists and we can build
    ensure_engine(config, engine, editor_is_running)
    click.secho('\nProject File Path: {}\nEngine Path: {}'.format(config.uproject_dir_path, config.UE4EnginePath))

    # Build UE4 Engine and Prereqs that might've gotten cleaned
    if not editor_is_running:
        tools_to_build = ['UnrealFrontend', 'ShaderCompileWorker', 'UnrealLightmass', 'CrashReportClient', 'UE4Editor']
        if not os.path.isfile(os.path.join(config.UE4EnginePath, 'Engine\\Binaries\\Win64\\UnrealHeaderTool.exe')):
            tools_to_build.insert(0, 'UnrealHeaderTool')
        for tool_name in tools_to_build:
            b = Build(config, build_name=tool_name)
            if not b.run():
                error_exit(b.error)
    else:
        print_warning('Skipping engine and tools build because engine is running!')

    run_build_steps(config, build_meta, 'pre_build_steps')

    if config.build_type == "Game":
        if editor_is_running:
            print_warning('Cannot build the Game+Editor while the editor is running!')
            click.pause()
            sys.exit(1)

        if 'game_editor_steps' in config.script:
            run_build_steps(config, build_meta, 'game_editor_steps')
        else:
            b = Build(config, build_name='Editor', is_game_project=True)
            if not b.run():
                error_exit(b.error)

    elif config.build_type == "Package":
        if editor_is_running:
            print_warning('You are packaging while also running the editor. '
                          'This could fail because of memory contraints.')
        if 'package_steps' in config.script:
            run_build_steps(config, build_meta, 'package_steps')
        else:
            package = Package(config)
            if not package.run():
                error_exit(package.error)

    run_build_steps(config, build_meta, 'post_build_steps')

    build_meta.save_meta()
    print_action('SUCCESS!')
    click.pause()


def ensure_engine(config, engine_override, editor_running):
    """
    Pre-work step of ensuring we have a valid engine and enough components exist to do work
    :param config: The project configuration (may not point to a valid engine yet)
    :param engine_override: The desired engine directory path to use
    :param editor_running: Is the engine currently running?
    """
    can_pull_engine = config.git_repo != '' and config.git_proj_branch != ''

    if config.UE4EnginePath == '':
        if config.clean:
            error_exit('Unable to clean. No Engine Found!')

        if not can_pull_engine and engine_override == '':
            error_exit('Static engine placement required for non-git pulled engine. '
                       'You can specify a path using the -e param, or specify git configuration.')

        if engine_override != '':
            config.setup_engine_paths(os.path.abspath(engine_override))
        else:
            result = click.confirm('Would you like to specify the location of the engine install?', default=False)
            if result:
                result = click.prompt('Where would you like to install the engine?')
                if not os.path.exists(result):
                    try:
                        os.makedirs(result)
                    except Exception:
                        error_exit('Unable to create engine directory! Tried @ {}'.format(result))
                config.setup_engine_paths(result)
            else:
                # Find an ideal location to put the engine
                engine_path = os.path.abspath(os.path.join(config.uproject_dir_path,
                                                           '..\\UnrealEngine_{}'.format(config.uproject_name)))
                if not os.path.exists(engine_path):
                    try:
                        os.makedirs(engine_path)
                    except Exception:
                        error_exit('Unable to create engine directory! Tried @ {}'.format(engine_path))
                config.setup_engine_paths(engine_path)
    elif config.UE4EnginePath != engine_override and engine_override != '':
        error_exit('Specific engine path requested, but engine path for this project already exists?')

    # Before doing anything, make sure we have all build dependencies ready
    if not config.clean and can_pull_engine:
        if not pull_git_engine(config, False):
            error_exit('Git Pull Failure!')

    if not config.setup_engine_paths(engine_override):
        error_exit('Could not setup valid engine paths!')

    # Register the engine (might do nothing if already registered)
    # If no key name, this is an un-keyed static engine.
    if config.UE4EngineKeyName != '':
        register_project_engine(config, False)

    if not editor_running:
        print_action('Checking engine dependencies up-to-date')

        def add_dep_exclude(path_name, args):
            args.append('-exclude={}'.format(path_name))

        cmd_args = []
        if config.exclude_samples:
            for sample_pack in ['FeaturePacks', 'Samples', 'Templates']:
                add_dep_exclude(sample_pack, cmd_args)
        for extra_exclude in config.extra_dependency_excludes:
            add_dep_exclude(extra_exclude, cmd_args)

        if launch(config.UE4GitDependenciesPath, cmd_args) != 0:
            error_exit('Engine dependencies Failed to Sync!')

        if not os.path.isfile(config.UE4UBTPath):
            # The unreal build tool does not exist, we need to build it first
            # We use the generate project files batch script because it ensures the build tool exists,
            # and builds it if not.
            print_action("Build tool doesn't exist yet, generating project and building...")
            if launch(config.UE4GenProjFilesPath, ['-2017'] if get_visual_studio_version() == 2017 else []) != 0:
                error_exit('Failed to build UnrealBuildTool.exe!')


def run_build_steps(config: ProjectConfig, build_meta: BuildMeta, steps_name, complain_missing_step: bool=False):
    """
    Runs the build steps defined in a build script.
    A valid script json must be loaded in config!
    :param config: The configuration for this project
    :param build_meta: Build meta which might contain requirements for a build step
    :param steps_name: The steps to perform, defined in the script
    :param complain_missing_step: True if you would like the steps runner to complain about this step not existing.
    """
    if config.script is None:
        print_warning('Script json not loaded for run_build_steps!')
        return

    if steps_name in config.script:
        steps = config.script[steps_name]
        for step in steps:
            if "enabled" in step and step["enabled"] is False:
                continue

            print_action('Performing Undescribed step' if 'desc' not in step else step['desc'])

            # Get the step class
            step_module = importlib.import_module(step['action']['module'])
            class_name = step['action']['module'].split('.')[-1]
            action_class = getattr(step_module, class_name.title(), None)
            if action_class is None:
                print_warning('action class ({}) could not be found!'.format(class_name.title()))
                continue

            # Create kwargs of requested arguments
            kwargs = {}
            if 'meta' in step['action']:
                kwargs.update(build_meta.collect_meta(step['action']['meta']))

            if 'args' in step['action']:
                kwargs.update(step['action']['args'])

            # Run the action
            # We deep copy the configuration so it cannot be tampered with from inside the action.
            b = action_class(deepcopy(config), **kwargs)
            if not b.run():
                if "allow_failure" in step and step["allow_failure"] is True:
                    print_warning(b.error)
                else:
                    error_exit(b.error)

            # Do meta updates
            if 'meta_updates' in step['action']:
                for k, v in step['action']['meta_updates'].items():
                    meta_item = getattr(b, v, None)
                    if meta_item is not None:
                        setattr(build_meta, k, meta_item)
                build_meta.save_meta()
    elif complain_missing_step:
        print_warning('Could not find build step ({}) for run_build_steps!'.format(steps_name))

if __name__ == "__main__":
    try:
        build_script()
    except Exception as e:
        error_exit('{}'.format(e))
