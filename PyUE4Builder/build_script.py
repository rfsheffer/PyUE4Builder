#!/usr/bin/env python

import sys
import os
import click
import json
import importlib
from build_meta import BuildMeta
from config import ProjectConfig, project_build_types, project_configurations, project_package_types
from utility.common import launch, print_title, print_action, error_exit, print_error, pull_git_engine, \
    ensure_engine_dependencies, get_visual_studio_version, register_project_engine, print_warning, is_editor_running
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
        tools_to_build = ['UnrealHeaderTool', 'UnrealFrontend', 'ShaderCompileWorker', 'UnrealLightmass',
                          'CrashReportClient', 'UE4Editor']
        for tool_name in tools_to_build:
            b = Build(config, build_name=tool_name)
            if not b.run():
                error_exit(b.error)
    else:
        print_warning('Skipping engine and tools build because engine is running!')

    if config.build_type == "Game":
        if editor_is_running:
            print_warning('Cannot build the Game+Editor while the editor is running!')
            click.pause()
            sys.exit(1)

        run_build_steps(config, build_meta, 'pre_game_editor_steps')

        # Now build the game project itself
        if config.uproject_editor_name != '':
            b = Build(config, build_name=config.uproject_editor_name, uproj_path=config.uproject_file_path)
            if not b.run():
                error_exit(b.error)
        else:
            print_warning('There is no Game+Editor project defined in configuration! Set ')

        run_build_steps(config, build_meta, 'post_game_editor_steps')
    elif config.build_type == "Package":
        run_build_steps(config, build_meta, 'pre_package_steps')
        package = Package(config)
        if not package.run():
            error_exit(package.error)
        run_build_steps(config, build_meta, 'post_package_steps')

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
        if not ensure_engine_dependencies(config):
            error_exit('Engine dependencies Failure!')

        if not os.path.exists(config.UE4UBTPath):
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

            # Run the action
            b = action_class(config, **kwargs)
            if not b.run():
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
