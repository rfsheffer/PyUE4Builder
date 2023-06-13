# PyUE4Builder
PyUE4Builder is a tool for simplifying the process of building an Unreal Engine 4/5 project. It helps in cases where you would like the project to be built and packaged on continuous integration, or you would like the process of using a custom unreal engine painless for non-technical employees.

Supports Unreal Engine 4.15-4.27 and Unreal 5.0-5.2

# The Why
Packaging a custom engine and distributing it to your artists/designers can be time-consuming. If edits to the engine are made commonly, you have to either include the entire pre-built install engine on your VCS (100gb+ of intermediate data) or package it up and re-distribute whenever changes are made, then help all artists/designers get up to speed each time. After doing this enough times, I decided I was wasting far too much time.

I devised these automation scripts for pulling our custom engine from github and building the engine plus game, while also ensuring the environment was able to do the work required and offering useful warnings or errors. This helps guide the user to a successful build or gives enough information for a programmer to help immediately without debugging.

# Key Features
* Ensures the user's environment is able to build the Unreal Engine and offers useful information for fixing issues with the environment.
* Pulling a custom UE4 engine from github (or just vanilla from Epics Repo)
* One click onboarding for new developers. Run the build script, and the builder does the rest.
* Automation of building the engine and your project locally or in CI
* Packaging your project into flavors
* Create new pre or post-build steps for your project by adding new actions written in python and adding them to your projects build script

# Requirements
* Windows machine
* Git for windows installed and git LFS for good measure
* Visual Studio (2017, 2019, 2022.. whatever the engine version requires) with unreal prerequisites
* Visual Studio prerequisites for C++ game development and .Net. See the Unreal Engine prerequisites page for the version of Unreal you are targetting.
* Python 3+ with the click module

# Notes
While the project only supports windows right now, that is only because the cached paths to tools are expecting .exe binaries. It would be trivial to support Linux or Mac, but I won't be doing this work unless I need to develop for those platforms.

# Integration
You can either use an auto script to pull this project down so it stays up to date, or just update it manually by grabbing the zip.

# Tool Breakdown
The projects PyUE4Builder folder contains two main scripts which do different things:

**build_script.py** This is the main script for building. It uses your configuration script as a guideline for building your project, and doing any extra pre or post steps.
###### Arguments:
* **--clean** This argument will try to clean up your project to get it back to a state before it was built.
* **--buildtype ['Game', 'Package']** Which type of build are you trying to create? Game+Editor OR Package?"
* **--configuration ['Shipping', 'Development', 'Debug']** This controls the configuration across a build. Development is default, Debug allows easier C++ debugging, Shipping builds in full optimization mode, and strips a lot development control from the running game.
* **--script** The build script to use, see the 'Build Script' section below.
* **--engine** This allows you to specify the location of the engine folder explicitly. Allows absolute and relative paths.

**tools.py** This script contains helpers for launching the editor and standalone, generating project files and building localization.
###### Arguments:
* **--script [Script Name]** The build script to use, see the 'Build Script' section below.

### Build Script
The build script is what tells the tool which project to build and how to build it.
#### Configuration
Here is a base script:
```json
{
	"config": {
		"project_path": "..\\MyGame.uproject",
		"engine_path_name": "",
		"git_proj_branch": "release",
		"git_repo": "git@github.com:EpicGames/UnrealEngine.git",
		"UE4EngineKeyName": "UnrealEngine_MyGame",
		"exclude_samples": true
	}
}
```
This script would expect a uproject called MyGame to be located one directory level below the tools root. It will try to search out the engine one directory level below the uproject directory.
It will pull the game engine if nessesary from Epics git repo, and pull the current release version of the engine. And it will register the engine in your systems registry as "UnrealEngine_MyGame".
Also, but having set "exclude_samples" to true, the 1.3gb of example content will not be pulled by epics git dependencies fetcher.

Here is a list of configuration settings:
* **project_path: str** The path (relative or absolute) of the uproject file.
* **engine_path_name: str** The path (relative or absolute) to the engine. Relative paths are from the uproject file.
* **git_proj_branch: str** The branch to use in git repo. Useful for targeting a specific engine version.
* **git_repo: str** The git repo you would like to pull the engine from. # ex: git@github.com:MyProject/UnrealEngine.git
* **UE4EngineKeyName: str** Registry keys and values related to unreal engine paths and our special engine name. If set to nothing, no registery checks or registration of the engine will be performed. This is useful for statically placed engines.
* **exclude_samples: bool** If true, the unreal dependency sync will ignore content samples (saving you about 1.4gb give or take). This is great for projects which have no need for content examples.
* **extra_dependency_excludes: [str]** If there are extra folders that should be ignored in the engines dependency pull, add them here. NOTE: The exclude_samples already excludes all extraneous sample folders. These are paths relative of the engine folder, ex. Engine/Extras/3dsMaxScripts

Note: You may add new configuration keys to the configuration file, and they will be queryable in your custom action scripts.
#### Actions
This section needs to be improved, but this is what action definitions look like within a build script:
```json
{
	...
	"game_editor_steps": [
		{
			"desc": "Game Editor",
			"action": {
				"module": "actions.build",
				"args": {
					"is_game_project": true,
					"build_name": "Editor"
				}
			}
		},
		{
			"desc": "Some action",
			"action": {
				"module": "myactions.myaction",
				"meta": ["variable_to_send_from_meta"],
				"meta_updates": {
					"variable_to_send_from_meta": "some_variable_that_was_updated"
				}
			}
		}
	]
}
```
There are 4 step sections which can be used right now: ["pre_build_steps", "game_editor_steps", "package_steps", "post_build_steps"]<br />
By default, if game_editor_steps and package_steps are not defined in the script, the builder will do a general build all pass for both. If you do include
a steps section, you must fill it in with the build steps you would like as no implicit action will be taken without them.

Inside an action module, there needs to be a class named exactly the same as your action module name, but the first character in the name must be capital.
Eventually the entire build system will be lists of actions.

# Usage Examples
Consider an unreal project to be in the folder D:/MyProjects/CoolProject/. Also consider that we want the engine to be in the MyProjects folder.<br />
We place PyUE4Builder into our MyProjects folder so it looks like this: D:/MyProjects/PyUE4Builder/<br />
We create a build script called "CoolProject_Build.json" in the CoolProject folder and it contains:
```json
{
	"config": {
		"project_path": "..\\CoolProject\\CoolProject.uproject",
		"engine_path_name": "",
		"uproject_editor_name": "CoolProjectEditor",
		"git_proj_branch": "release",
		"git_repo": "git@github.com:EpicGames/UnrealEngine.git",
		"UE4EngineKeyName": "UnrealEngine_MyEngine"
	}
}
```
We can then create some batch scripts to simplify starting the tool:<br />
D:/MyProjects/CoolProject/BuildMyProject.bat
```batch
%MY_PYTHON_PATH%\\python.exe ..\\PyUE4Builder\\PyUE4Builder\\build_script.py -s "CoolProject_Build.json" -t Game
```
D:/MyProjects/CoolProject/PackageProject.bat
```batch
%MY_PYTHON_PATH%\\python.exe ..\\PyUE4Builder\\PyUE4Builder\\build_script.py -s "CoolProject_Build.json" -t Package
```
D:/MyProjects/CoolProject/RunEditor.bat
```batch
%MY_PYTHON_PATH%\\python.exe ..\\PyUE4Builder\\PyUE4Builder\\tools.py -s "CoolProject_Build.json" runeditor
```
D:/MyProjects/CoolProject/RunStandalone.bat
```batch
%MY_PYTHON_PATH%\\python.exe ..\\PyUE4Builder\\PyUE4Builder\\tools.py -s "CoolProject_Build.json" standalone -e "-log"
```
D:/MyProjects/CoolProject/GenerateProjectFiles.bat
```batch
%MY_PYTHON_PATH%\\python.exe ..\\PyUE4Builder\\PyUE4Builder\\tools.py -s "CoolProject_Build.json" genproj
```
