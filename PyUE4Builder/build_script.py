#!/usr/bin/env python

import os
import click
import json
from config import ProjectConfig, project_configurations, platform_types
from utility.common import launch, print_title, print_action, error_exit, \
    get_visual_studio_version, register_project_engine
from actions.build import Build
from actions.package import Package
from actions.git import Git
from actions.buildsteps import Buildsteps

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer", "VREAL"]

is_automated = os.environ.get("PYUE4BUILDER_AUTOMATED", "0") == "1"


@click.command()
@click.option('--pause_always/--error_pause_only',
              default=True,
              show_default=True,
              help='Pause always or only pause on error?')
@click.option('--buildexplicit/--no-buildexplicit',
              default=False,
              show_default=True,
              help='Should the build system only build what is requested? This prevents convienience cases like '
                   'the package build building the editor before trying to package. By setting this to true, it is '
                   'expected that the user has setup the proper state before building.')
@click.option('--automated/--no-automated',
              default=False,
              show_default=True,
              help='Is this build being run on a continuous integration server? '
                   'The global environment should be left alone.')
@click.option('--clean/--no-clean',
              default=False,
              show_default=True,
              help='Causes all actions to consider cleaning up their workspaces before executing their action.')
@click.option('--platform', '-p',
              type=click.Choice(platform_types),
              default='Win64',
              show_default=True,
              help="Specifies the platform to build for. Defaults to Win64.")
@click.option('--build', '-b',
              default='',
              show_default=True,
              help="If set, specifies build steps to run and nothing more. Basic engine tools will not be built.")
@click.option('--buildtype', '-t',
              type=click.STRING,
              default='Editor',
              show_default=True,
              help="Which type of build are you trying to create? Editor OR Package?")
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
def build_script(engine, script, configuration, buildtype, build, platform, clean,
                 automated, buildexplicit, pause_always):
    """
    The Main call for build script execution.
    :param engine: The desired engine path, absolute or relative.
    :param script: The Project Script which defines the projects paths, build steps, and extra information.
    :param configuration: Build configuration, e.g. Shipping
    :param buildtype: Which type of build are you trying to create? Editor OR Package?
    :param build: Which build steps to execute?
    :param platform: Which platform to build for?
    :param clean: Causes all actions to consider cleaning up their workspaces before executing their action.
    :param automated: Configures the builder to recognize this build as being done by continuous integration and should
                      not manipulate the system environment.
    :param buildexplicit: Should the build system only build what is requested? This prevents convienience cases like
                          the package build building the editor before trying to package. By setting this to true, it is
                          expected that the user has setup the proper state before building.
    :param pause_always: Pause always or only pause on error?
    """
    # Fixup for old build type 'Game'.
    if buildtype == 'Game':
        buildtype = 'Editor'

    global is_automated
    if automated:
        is_automated = automated

    # Ensure Visual Studio is installed
    if get_visual_studio_version() == -1:
        error_exit('Cannot run build, visual studio install not found!', not is_automated)

    if not os.path.isfile(script):
        error_exit('Build script path is invalid. Check your -s argument.', not is_automated)

    with open(script, 'r') as fp:
        try:
            script_json = json.load(fp)
        except Exception as jsonError:
            error_exit('Build Script Syntax Error:\n{}'.format(jsonError), not is_automated)
            return

    config = ProjectConfig(configuration, platform, False, clean, automated)
    if not config.load_configuration(script_json, engine, buildexplicit):
        error_exit('Failed to load configuration. See errors above.', not config.automated)

    print_title('Unreal Project Builder')

    if config.automated:
        click.secho('\nAutomated flag set!')

    engine_branch_switched = False

    # Ensure the engine exists and we can build
    if not buildexplicit:
        engine_branch_switched = ensure_engine(config, engine)
        if engine_branch_switched:
            config.clean = True
    click.secho('\nProject File Path: {}\nEngine Path: {}'.format(config.uproject_dir_path, config.UE4EnginePath))

    if engine_branch_switched:
        click.secho('\nEngine Branch switched, will clean and rebuild...\n')

    # Ensure the unreal header tool exists. It is important for all Unreal projects
    if not buildexplicit:
        if not os.path.isfile(os.path.join(config.UE4EnginePath, 'Engine\\Binaries\\Win64\\UnrealHeaderTool.exe')):
            b = Build(config, build_name='UnrealHeaderTool')
            if not b.run():
                error_exit(b.error, not config.automated)

    # Build required engine tools
    if config.should_build_engine_tools and not buildexplicit:
        clean_revert = config.clean
        if buildtype == "Package" and not engine_branch_switched:
            config.clean = False  # Don't clean if packaging, waste of time

        b = Build(config, build_names=config.build_engine_tools)
        if not b.run():
            error_exit(b.error, not config.automated)

        config.clean = clean_revert

    # If a specific set of steps if being requested, only build those
    if build != '':
        steps = Buildsteps(config, steps_name=build)
        if not steps.run():
            error_exit(steps.error, not config.automated)
    else:
        if buildtype == "Editor":
            if config.editor_running:
                error_exit('Cannot build the Editor while the editor is running!', not config.automated)

            if 'game_editor_steps' in config.script:
                steps = Buildsteps(config, steps_name='game_editor_steps')
                if not steps.run():
                    error_exit(steps.error, not config.automated)
            elif 'editor_steps' in config.script:
                steps = Buildsteps(config, steps_name='editor_steps')
                if not steps.run():
                    error_exit(steps.error, not config.automated)
            else:
                b = Build(config, build_name='{}Editor'.format(config.uproject_name))
                if not b.run():
                    error_exit(b.error, not config.automated)

        elif buildtype == "Package":
            # We need to build the editor before we can run any cook commands. This seems important for blueprints
            # probably because it runs the engine and expects all of the native class RTTI to be up-to-date to be able
            # to compile the blueprints. Usually you would be starting a package build from the editor, so it makes
            # sense. Explicit builds ignore this however.
            if not buildexplicit:
                b = Build(config, build_name='{}Editor'.format(config.uproject_name))
                if not b.run():
                    error_exit(b.error, not config.automated)

            if 'package_steps' in config.script:
                steps = Buildsteps(config, steps_name='package_steps')
                if not steps.run():
                    error_exit(steps.error, not config.automated)
            else:
                package = Package(config)
                if not package.run():
                    error_exit(package.error, not config.automated)

    print_action('SUCCESS!')
    if not config.automated and pause_always:
        click.pause()


def ensure_engine(config, engine_override):
    """
    Pre-work step of ensuring we have a valid engine and enough components exist to do work
    :param config: The project configuration (may not point to a valid engine yet)
    :param engine_override: The desired engine directory path to use
    """
    can_pull_engine = config.git_engine_repo != '' and config.git_engine_branch != ''
    engine_branch_switched = False

    if config.UE4EnginePath == '':
        if not can_pull_engine and engine_override == '':
            error_exit('Static engine placement required for non-git pulled engine. '
                       'You can specify a path using the -e param, or specify git configuration.', not config.automated)

        if engine_override != '':
            config.setup_engine_paths(os.path.abspath(engine_override))
        elif not config.automated:
            result = click.confirm('Would you like to specify the location of the engine install?', default=False)
            if result:
                while True:
                    result = click.prompt('Where would you like to install the engine?')
                    if not os.path.isabs(result):
                        result = os.path.abspath(result)
                        ask_rel = click.confirm('This is a relative path expanding to {}\nIs this ok?'.format(result),
                                                default=False)
                        if not ask_rel:
                            continue
                    if not os.path.exists(result):
                        try:
                            os.makedirs(result)
                        except Exception:
                            error_exit('Unable to create engine directory! Tried at {}'.format(result),
                                       not config.automated)
                    config.setup_engine_paths(result)
                    break
            else:
                # Find an ideal location to put the engine
                if len(config.engine_path_name) == 0:
                    # Put the engine one directory down from the uproject
                    engine_path = os.path.abspath(os.path.join(config.uproject_dir_path,
                                                               '..\\UnrealEngine_{}'.format(config.uproject_name)))
                else:
                    if os.path.isabs(config.engine_path_name):
                        engine_path = config.engine_path_name
                    else:
                        engine_path = os.path.normpath(os.path.join(config.uproject_dir_path, config.engine_path_name))

                if not os.path.exists(engine_path):
                    try:
                        os.makedirs(engine_path)
                    except Exception:
                        error_exit('Unable to create engine directory! Tried @ {}'.format(engine_path),
                                   not config.automated)
                config.setup_engine_paths(engine_path)
        else:
            error_exit('No engine available for automated case! Either fill out git info or supply engine directory',
                       not config.automated)
    elif config.UE4EnginePath != engine_override and engine_override != '':
        error_exit('Specific engine path requested, but engine path for this project already exists?',
                   not config.automated)

    # Before doing anything, make sure we have all build dependencies ready
    if can_pull_engine:
        git_action = Git(config)
        git_action.branch_name = config.git_engine_branch
        git_action.similar_branches = config.git_engine_similar_branches
        git_action.repo_name = config.git_engine_repo
        git_action.output_folder = config.UE4EnginePath
        git_action.disable_strict_hostkey_check = True
        git_action.force_repull = False
        if not git_action.run():
            error_exit(git_action.error, not config.automated)
        engine_branch_switched = git_action.branch_switched

    if not config.setup_engine_paths(engine_override):
        error_exit('Could not setup valid engine paths!', not config.automated)

    # Make sure we have the build tools required for this engine version
    if get_visual_studio_version(config.get_suitable_vs_versions()) == -1:
        error_exit('Cannot find a version of visual studio required to build this engine version. Expecting {}'.format(config.get_suitable_vs_versions()), not config.automated)

    # Register the engine (might do nothing if already registered)
    # If no key name, this is an un-keyed static engine.
    if config.UE4EngineKeyName != '' and not config.automated:
        register_project_engine(config, False)

    if not config.editor_running:
        print_action('Checking engine dependencies up-to-date')

        def add_dep_exclude(path_name, args):
            args.append('-exclude={}'.format(path_name))

        cmd_args = []
        if config.force_dependencies:
            cmd_args.append('--force')
        if config.exclude_samples:
            for sample_pack in ['FeaturePacks', 'Samples']:
                add_dep_exclude(sample_pack, cmd_args)
        for extra_exclude in config.extra_dependency_excludes:
            add_dep_exclude(extra_exclude, cmd_args)

        if launch(config.UE4GitDependenciesPath, cmd_args) != 0:
            error_exit('Engine dependencies Failed to Sync!', not config.automated)

        if not os.path.isfile(config.UE4UBTPath):
            # The unreal build tool does not exist, we need to build it first
            # We use the generate project files batch script because it ensures the build tool exists,
            # and builds it if not.
            print_action("Build tool doesn't exist yet, generating project and building...")
            extra_args = ['-VS{}'.format(get_visual_studio_version(config.get_suitable_vs_versions()))]
            if launch(config.UE4GenProjFilesPath, extra_args) != 0:
                error_exit('Failed to build UnrealBuildTool.exe!', not config.automated)
    return engine_branch_switched

if __name__ == "__main__":
    try:
        build_script()
    except Exception as e:
        error_exit('{}'.format(e), not is_automated)
