#!/usr/bin/env python

from actions.action import Action
from utility.common import print_action
import importlib
from copy import deepcopy
from build_meta import BuildMeta

__author__ = "Ryan Sheffer"
__copyright__ = "Copyright 2020, Sheffer Online Services"
__credits__ = ["Ryan Sheffer", "VREAL"]


class Buildsteps(Action):
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
        self.previous_meta = kwargs['build_meta'] if 'build_meta' in kwargs else None

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

        # If this is a sub build steps, it continues the meta of the previous steps
        if self.previous_meta is not None:
            for k, v in self.previous_meta.__dict__.items():
                setattr(build_meta, k, v)

        # Push steps meta
        for k, v in self.push_meta.items():
            setattr(build_meta, k, v)

        steps = self.config.script[self.steps_name]
        for step in steps:
            if "enabled" in step and step["enabled"] is False:
                continue

            # Check step conditions
            # comma separated conditions using 'not' for negation.
            # Conditions are vars found in meta or config, ex: "not automated, clean"
            conditions_passed = True
            cond_not_met = ''
            if "condition" in step:
                try:
                    cond_splits = step["condition"].split(' ')
                    cur_index = 0
                    while cur_index < len(cond_splits):
                        cond = True
                        if cond_splits[cur_index] == 'not':
                            cur_index += 1
                            cond_to_check = cond_splits[cur_index]
                            cond = False
                        else:
                            cond_to_check = cond_splits[cur_index]
                        cond_to_check = cond_to_check.replace(',', '')

                        # Get the attribute from either meta or config
                        attr_to_test = None
                        if hasattr(build_meta, cond_to_check):
                            attr_to_test = getattr(build_meta, cond_to_check)
                            if type(attr_to_test) is not bool:
                                attr_to_test = None
                        elif hasattr(self.config, cond_to_check):
                            attr_to_test = getattr(self.config, cond_to_check)
                            if type(attr_to_test) is not bool:
                                attr_to_test = None

                        # Test the attribute against our condition
                        if attr_to_test is not None:
                            if cond != attr_to_test:
                                conditions_passed = False
                                if cond:
                                    cond_not_met = cond_to_check
                                else:
                                    cond_not_met = 'not {0}'.format(cond_to_check)
                                break

                        cur_index += 1
                except Exception:
                    self.error = 'Invalid conditional statement!'
                    return False

            if not conditions_passed:
                step_name = 'unknown' if 'desc' not in step else step['desc']
                self.warning('Skipping ({0}) step because condition ({1}) was not met'.format(step_name, cond_not_met))
                continue

            print_action('Performing un-described step' if 'desc' not in step else step['desc'])

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
