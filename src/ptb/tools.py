#!/home/takacs/projects/ptb/venv/ptb/bin/python --

"""
tools that do not fit anywhere else 
"""

import random
import collections
import copy
import contextlib
import numpy as np

@contextlib.contextmanager
def dummy_context_mgr():
    yield None

def rand_tag(length: int=8):
    """generate a lorem ipsum string (pronouncable but meaningless) """
    
    cons = 'BCDFGHJKLMNPRSTVWYZ'
    vowels = 'AEIOU'

    # Extremely Dummy Markov chain. Choose inital set randomly, then stay
    # here with a 20% probability, but always switch if the previous kept the
    # original state

    tag = ""

    is_vowel = random.uniform(0,1) > 0.5
    force = True

    for _ in range(0, length):
    
        change = random.uniform(0,1) > 0.2
        
        if is_vowel:
            tag += vowels[ random.randint(0, len(vowels)-1) ]
            if force or change:
                is_vowel = False
            force = is_vowel
        else:
            tag += cons[ random.randint(0, len(cons)-1) ]
            if force or change:
                is_vowel = True
            force = not is_vowel
    
    return tag

def set_object_properties(instance, d: dict):
    """Sets properties that exist in the object to the value in the dictionary.
       Skips values that are not present as property of the object."""
       
    for key, val in d.items():
        if hasattr(instance, key):
            valtype = type(getattr(instance, key))
            setattr(instance, key, valtype(val))
            
def recursive_dict_merge(base_dct: dict, merge_dct: dict, add_keys=True):    
    """recursive dict merge by keys"""
    rtn_dct = copy.deepcopy(base_dct)
        
    if add_keys is False:
        merge_dct = { key: merge_dct[key] for key in set(rtn_dct).intersection(set(merge_dct)) }

    rtn_dct.update( {
        key: recursive_dict_merge(rtn_dct[key], merge_dct[key], add_keys=add_keys)
        if isinstance(rtn_dct.get(key), dict) and isinstance(merge_dct[key], dict)
        else merge_dct[key]
        for key in merge_dct.keys()
        } )            
    
    return rtn_dct

