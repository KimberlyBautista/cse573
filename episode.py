""" Contains the Episodes for Navigation. """
import random
import torch
import time
import sys
from constants import GOAL_SUCCESS_REWARD, STEP_PENALTY, BASIC_ACTIONS
from environment import Environment
from utils.net_util import gpuify


class Episode:
    """ Episode for Navigation. """
    def __init__(self, args, gpu_id, rank, strict_done=False):
        super(Episode, self).__init__()

        self._env = None

        self.gpu_id = gpu_id
        self.strict_done = strict_done
        self.task_data = None
        self.glove_embedding = None

        self.seed = args.seed + rank
        random.seed(self.seed)

        with open('./datasets/objects/int_objects.txt') as f:
            int_objects = [s.strip() for s in f.readlines()]
        with open('./datasets/objects/rec_objects.txt') as f:
            rec_objects = [s.strip() for s in f.readlines()]
        
        self.objects = int_objects + rec_objects

        self.actions_list = [{'action':a} for a in BASIC_ACTIONS]
        self.actions_taken = []

    @property
    def environment(self):
        return self._env

    def state_for_agent(self):
        return (self.environment.current_frame, self.triedFind)

    def step(self, action_as_int):
        action = self.actions_list[action_as_int]
        self.actions_taken.append(action)
        return self.action_step(action)

    def action_step(self, action):
        self.environment.step(action)
        reward, terminal, action_was_successful = self.judge(action)

        return reward, terminal, action_was_successful

    def slow_replay(self, delay=0.2):
        # Reset the episode
        self._env.reset(self.cur_scene, change_seed = False)
        
        for action in self.actions_taken:
            self.action_step(action)
            time.sleep(delay)
    
    def judge(self, action):
        """ Judge the last event. """
        # immediate reward
        reward = STEP_PENALTY 
        done = False
        action_was_successful = self.environment.last_action_success

        '''
        if action['action'] == 'LookObject':
            self.triedFind['Tomato'] = True
            self.triedFind['Bowl'] = True
            objects = self._env.last_event.metadata['objects']
            visible_objects = [o['objectType'] for o in objects if o['visible']]
            if 'Tomato' in visible_objects and (self.target['Tomato'] == False) :
                self.target['Tomato'] = True
                reward += GOAL_SUCCESS_REWARD
            if 'Bowl' in visible_objects and (self.target['Bowl'] == False):
                self.target['Bowl'] = True
                reward += GOAL_SUCCESS_REWARD
        '''
        if action['action'] == 'LookTomato':
            objects = self._env.last_event.metadata['objects']
            for o in objects:
                if o['visible'] and o['objectType'] == 'Tomato' and self.target['Tomato'] == False: # Check if already picked up
                    tomato_id = o['objectId']
                    self.cookId['Tomato'] = tomato_id
                    is_tomato_picked_up = self._env.pickup_tomato(tomato_id)

                    if is_tomato_picked_up:
                        self.triedFind['Tomato'] = True
                        self.target['Tomato'] = True
                        reward += GOAL_SUCCESS_REWARD
            # visible_objects = [o['objectType'] for o in objects if o['visible']]
            # if 'Tomato' in visible_objects and (self.target['Tomato'] == False) :
            #     self.target['Tomato'] = True
            #     reward += GOAL_SUCCESS_REWARD

        if action['action'] == 'LookMicrowave':
            self.triedFind['Microwave'] = True

            objects = self._env.last_event.metadata['objects']
            for o in objects:
                if o['visible'] and o['objectType'] == 'Microwave' and self.target['Microwave'] == False:  # Check if already picked up
                    microwave_id = o['objectId']
                    self.cookId['Microwave'] = microwave_id
                    is_cooked = self._env.cook_tomato(microwave_id, self.cookId['Tomato'])

                    if is_cooked:
                        self.target['Microwave'] = True
                        reward += GOAL_SUCCESS_REWARD
            # objects = self._env.last_event.metadata['objects']
            # visible_objects = [o['objectType'] for o in objects if o['visible']]
            # if 'Bowl' in visible_objects and (self.target['Bowl'] == False):
            #     self.target['Bowl'] = True
            #     reward += GOAL_SUCCESS_REWARD

        if action['action'] == 'Done':
            done = True
            #objects = self._env.last_event.metadata['objects']
            #visible_objects = [o['objectType'] for o in objects if o['visible']]
            #if self.target in visible_objects:
            #    reward += GOAL_SUCCESS_REWARD
            self.success = self.target['Microwave'] and self.target['Tomato']
            if self.success:
                reward += GOAL_SUCCESS_REWARD

        return reward, done, action_was_successful

    def new_episode(self, args, scene):
        
        if self._env is None:
            if args.arch == 'osx':
                local_executable_path = './datasets/builds/thor-local-OSXIntel64.app/Contents/MacOS/thor-local-OSXIntel64'
            else:
                local_executable_path = './datasets/builds/thor-local-Linux64'
            
            self._env = Environment(
                    grid_size=args.grid_size,
                    fov=args.fov,
                    local_executable_path=local_executable_path,
                    randomize_objects=args.randomize_objects,
                    seed=self.seed)
            self._env.start(scene, self.gpu_id)
        else:
            self._env.reset(scene)

        # For now, single target.
        self.target = {'Tomato':False,'Microwave':False}
        self.cookId = {'Tomato':-1,'Microwave':-1}
        self.triedFind = {'Tomato':False, 'Microwave':False}
        self.success = False
        self.cur_scene = scene
        self.actions_taken = []
        
        return True
