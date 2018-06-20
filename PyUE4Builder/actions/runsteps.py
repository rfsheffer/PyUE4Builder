#!/usr/bin/env python

from actions.action import Action
from utility.common import print_action
import importlib
from copy import deepcopy
from build_meta import BuildMeta

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2018, Ryan Sheffer Open Source"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Runsteps(Action):
    """
    Run Steps Action
    An action designed to run a list of steps found within the build script
    This action is used as the baseline for running steps, but can also be added as an action in build steps
    for cases where more complicated build systems exist where a master list of steps exist for a type of build which
    contain a number of sub-build-steps with specialized parameters.
    For example: One build might add certain pre-processor defines over another type of build.
    """

    def __init__(self, config, **kwargs):
        super().__init__(config, **kwargs)
        self.steps_name = kwargs['steps_name'] if 'steps_name' in kwargs else ''
        self.push_meta = kwargs['push_meta'] if 'push_meta' in kwargs else {}
        self.complain_missing_step = kwargs['complain_missing_step'] if 'complain_missing_step' in kwargs else True

    @staticmethod
    def get_arg_docs():
        return {
            'steps_name': 'The steps to perform, defined in the script',
            'push_meta': 'Pass a dict of meta overrides for these steps. Useful for specialization.',
            'complain_missing_step': 'True if you would like the steps runner to complain about this step not existing.'
        }

    def verify(self):
        if len(self.steps_name) == 0:
            return 'Steps name is not set!'
        if self.steps_name not in self.config.script and self.complain_missing_step:
            return 'Invalid build steps name {}'.format(self.steps_name)
        return ''

    def run(self):
        base_build_meta = BuildMeta('project_build_meta')
        build_meta = deepcopy(base_build_meta)

        # Push steps meta
        for k, v in self.push_meta.items():
            setattr(build_meta, k, v)

        steps = self.config.script[self.steps_name]
        for step in steps:
            if "enabled" in step and step["enabled"] is False:
                continue

            print_action('Performing Undescribed step' if 'desc' not in step else step['desc'])

            # Get the step class
            step_module = importlib.import_module(step['action']['module'])
            class_name = step['action']['module'].split('.')[-1]
            action_class = getattr(step_module, class_name.title(), None)
            if action_class is None:
                self.error = 'action class ({}) could not be found!'.format(class_name.title())
                return False

            # Create kwargs of requested arguments
            kwargs = {'build_meta': build_meta}
            if 'args' in step['action']:
                kwargs.update(step['action']['args'])

            # Run the action
            # We deep copy the configuration so it cannot be tampered with from inside the action.
            b = action_class(deepcopy(self.config), **kwargs)
            verify_error = b.verify()
            if verify_error != '':
                if "allow_failure" in step and step["allow_failure"] is True:
                    self.warning(verify_error)
                    self.warning('Verification of this action failed. Skipping because of allow_failure flag.')
                    continue
                else:
                    self.error = verify_error
                    return False

            if not b.run():
                if "allow_failure" in step and step["allow_failure"] is True:
                    self.warning(b.error)
                    self.warning('Running of this action failed. Skipping because of allow_failure flag.')
                    continue
                else:
                    self.error = b.error
                    return False

            # Persist meta updates globally (this persists meta beyond program scope)
            if 'persist_meta' in step['action']:
                for k, v in step['action']['persist_meta'].items():
                    meta_item = getattr(b, v, None)
                    if meta_item is not None:
                        setattr(base_build_meta, k, meta_item)
                        setattr(build_meta, k, meta_item)
                base_build_meta.save_meta()
            # Push meta updates to local meta
            if 'push_meta' in step['action']:
                for k, v in step['action']['push_meta'].items():
                    meta_item = getattr(b, v, None)
                    if meta_item is not None:
                        setattr(build_meta, k, meta_item)
        return True
