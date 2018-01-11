#!/usr/bin/env python

import os
import re
from copy import deepcopy
from pathlib import Path
from winregistry import WinRegistry as Reg
from utility.common import check_engine_dir_valid

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]

project_configurations = ['Shipping', 'Development', 'Debug']
project_build_types = ['Game', 'Package']

# The names of the platforms the engine understands
platform_types = ['Win32', 'Win64', "Linux", "Android", "IOS", "TVOS", "Mac", "PS4", "XboxOne", "Switch"]

# The names prepended to output build folders for platforms
platform_long_names = ["Windows", "Windows", "Linux", "Android", "IOS", "TVOS", "Mac", "PS4", "XboxOne", "Switch"]


class ProjectConfig(object):
    """
    Common configuration and paths for unreal project automation processes
    Extra variables are injected via the build scripts
    """
    def __init__(self, configuration="Development", build_type="Game", clean=False):
        # Build Switches
        self.configuration = configuration
        self.build_type = build_type
        self.clean = clean

        # The loaded script json for the project. Keeping around for the build process.
        self.script = None

        # Path to where package builds are placed
        self.builds_path = ''

        # The name of the uproject
        self.uproject_name = ''
        # This is the path to the project directory
        self.uproject_dir_path = ''
        # This is the path to the unreal project file in the project directory
        self.uproject_file_path = ''
        # This is the path to the localization compile script
        self.proj_localization_script = ''

        # If true, the unreal dependency sync will ignore content samples (saving you about 1.4gb give or take)
        # This is great for projects which have no need for content examples.
        self.exclude_samples = False

        # If there are extra folders that should be ignored in the engines dependency pull, add them here.
        # NOTE: The exclude_samples already excludes all extraneous sample folders
        # These are paths relative of the engine folder, ex. Engine/Extras/3dsMaxScripts
        self.extra_dependency_excludes = []

        # The path (relative or absolute) of the uproject file.
        self.project_path = ''

        # This is the version string assciated with this project. It is fetched from the projects
        # DefaultGame.ini ex. ProjectVersion=1.0.0.0
        self.version_str = '1.0.0.0'

        # Relative path from the uproject directly to the engine.
        self.engine_path_name = ''

        # Git Config
        self.git_proj_branch = ''  # The branch to use in git repo
        self.git_repo = ''  # ex: git@github.com:MyProject/UnrealEngine.git

        # Registry keys and values related to unreal engine paths and our special engine name
        # If set to nothing, no registery checks or registration of the engine will be performed.
        # This is useful for statically placed engines.
        self.UE4EngineKeyName = ''  # ex. UnrealEngine_MyProject

        self.UE4EngineBuildsReg = r'HKEY_CURRENT_USER\SOFTWARE\Epic Games\Unreal Engine\Builds'

        # Engine Tools. These get set in setup_environment.
        self.UE4EnginePath = ''
        self.UE4GenProjFilesPath = ''
        self.UE4GitDependenciesPath = ''
        self.UE4EnginePrereqPath = ''
        self.UE4UBTPath = ''
        self.UE4RunUATBatPath = ''
        self.UE4BuildBatchPath = ''
        self.UE4CleanBatchPath = ''
        self.UE4EditorPath = ''
        self.UE4VersionSelectorPath = ''

    def load_configuration(self, script_json, custom_engine_path='', ensure_engine=True):
        """
        Load the configuration from a build script
        :param script_json: Script json structured building information
        :param custom_engine_path: The custom engine path override to use
        :param ensure_engine: If true, this function returns false if no engine could be found
        :return True if everything is ok
        """
        from utility.common import print_error
        if self.configuration not in project_configurations:
            print_error('Invalid Configuration!')
            return False
        if self.build_type not in project_build_types:
            print_error('Invalid Configuration!')
            return False

        try:
            self.script = deepcopy(script_json)
            for k, v in self.script["config"].items():
                setattr(self, k, deepcopy(v))
        except Exception as e:
            print_error(e)
            return False

        self.uproject_name = os.path.splitext(os.path.basename(self.project_path))[0]
        self.uproject_dir_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                              '..\\',
                                                              os.path.dirname(self.project_path)))
        self.uproject_file_path = os.path.join(self.uproject_dir_path, '{}.uproject'.format(self.uproject_name))
        if not os.path.isfile(self.uproject_file_path):
            print_error('Invalid uproject path ({})! '
                        'Check your project_path configuration.'.format(self.uproject_file_path))
            return False
        self.proj_localization_script = os.path.join(self.uproject_dir_path, 'Config\\Localization\\Game.ini')

        # Try to fetch the version string. A couple common things can go wrong like the default game being missing
        # or the line being missing from the file.
        try:
            str_out = self.get_game_ini_version_number(os.path.join(self.uproject_dir_path, 'Config\\DefaultGame.ini'))
            if str_out is not None:
                self.version_str = str_out
        except Exception:
            pass

        self.builds_path = os.path.join(self.uproject_dir_path, 'builds')

        if not self.setup_engine_paths(custom_engine_path) and ensure_engine:
            print_error("No engine could be found!")
            return False
        return True

    def setup_engine_paths(self, custom_engine_path=''):
        # Assume the engine is just back from our project directory. Or check the registry to see where
        # it actually resides.
        if self.UE4EnginePath != '' and custom_engine_path == '':
            return True  # No need, already setup

        result = True
        # Initially do the obvious search, one path back from the project directory
        self.UE4EnginePath = os.path.abspath(os.path.join(self.uproject_dir_path, '..\\', self.engine_path_name))
        if custom_engine_path != '':
            self.UE4EnginePath = custom_engine_path
        if self.UE4EngineKeyName != '' and not os.path.isdir(self.UE4EnginePath):
            # search the registry and see if the engine is registered elsewhere
            reg = Reg()
            try:
                registered_engines = reg.read_key(self.UE4EngineBuildsReg)['values']
                for engine in registered_engines:
                    if engine['value'] == self.UE4EngineKeyName:
                        # this is it!
                        self.UE4EnginePath = engine['data']
                        break
                else:
                    self.UE4EnginePath = ''
                    result = False
            except Exception:
                # No keys exist, fresh install!
                self.UE4EnginePath = ''
                result = False
        else:
            result = check_engine_dir_valid(self.UE4EnginePath)

        # Set all absolute paths to unreal tools
        self.UE4GenProjFilesPath = str(Path(self.UE4EnginePath, 'Engine\\Build\\BatchFiles\\GenerateProjectFiles.bat'))
        self.UE4GitDependenciesPath = str(Path(self.UE4EnginePath, 'Engine\\Binaries\\DotNET\\GitDependencies.exe'))
        self.UE4EnginePrereqPath = str(Path(self.UE4EnginePath,
                                            'Engine\\Extras\\Redist\\en-us\\UE4PrereqSetup_x64.exe'))
        self.UE4UBTPath = str(Path(self.UE4EnginePath, 'Engine\\Binaries\\DotNET\\UnrealBuildTool.exe'))
        self.UE4RunUATBatPath = str(Path(self.UE4EnginePath, 'Engine\\Build\\BatchFiles\\RunUAT.bat'))
        self.UE4BuildBatchPath = str(Path(self.UE4EnginePath, 'Engine\\Build\\BatchFiles\\Build.bat'))
        self.UE4CleanBatchPath = str(Path(self.UE4EnginePath, 'Engine\\Build\\BatchFiles\\Clean.bat'))
        self.UE4EditorPath = str(Path(self.UE4EnginePath, 'Engine\\Binaries\\Win64\\UE4Editor.exe'))
        self.UE4VersionSelectorPath = str(Path(self.UE4EnginePath,
                                               'Engine\\Binaries\\Win64\\UnrealVersionSelector-Win64-Shipping.exe'))
        return result

    def check_environment(self):
        """
        Check that the environment is sound for building
        :return: True if the environment looks good
        """
        if not os.path.isdir(self.UE4EnginePath) \
                or not os.path.isfile(self.UE4EditorPath) \
                or not os.path.isfile(self.UE4UBTPath) \
                or not os.path.isfile(self.UE4RunUATBatPath):
            from utility.common import print_error
            print_error('Unable to find the engine!')
            return False
        return True

    @staticmethod
    def get_game_ini_version_number(ini_file):
        """
        From an unreal engine ini containing our version string, pull that version string and return it
        :param ini_file: The ini to find
        :return: The version string, or None if not found
        """
        version_number = None
        with open(ini_file, "r") as file:
            p = re.compile("ProjectVersion\s*=\s*(?P<version>\S+)")
            for line in file:
                m = p.match(line)
                if m is not None:
                    version_number = m.group('version')
                    break
        return version_number
