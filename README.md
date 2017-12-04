# PyUE4Builder
PyUE4Builder is a tool for simplifying the process of building an Unreal Engine 4 project. It helps in cases where you would like the project to be built and packaged on continuous integration, or you would like the process of using a custom unreal engine painless for non-technical employees.

# The Why
Packaging a custom engine and distributing it to your artists/designers can be time-consuming. If edits to the engine are made commonly, you have to either include the entire pre-built install engine on your VCS (40gb of intermediate data) or package it up and re-distribute whenever changes are made, then help all artists/designers get up to speed each time. After doing this enough times, I decided I was wasting far too much time.

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
* Visual Studio 2015 or 2017 with unreal prerequisites
* Python 3+ with the click module

# Notes
While the project only supports windows right now, that is only because the cached paths to tools are expecting .exe binaries. It would be trivial to support Linux or Mac, but I won't be doing this work unless I need to develop for those platforms.

# Integration
TODO

# Usage Examples
TODO
