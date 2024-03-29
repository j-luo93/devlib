import os
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

from arglib import (Registry, add_argument, add_registry, g, get_configs,
                    parse_args, set_argument)
from trainlib import create_logger


def _is_in_git_repo() -> bool:
    res = subprocess.run('git rev-parse --is-inside-work-tree', shell=True, capture_output=True)
    if res.returncode == 127:
        raise OSError('git not installed.')
    elif res.returncode != 0:
        raise OSError('Some git-related error.')
    else:
        output = res.stdout.decode('utf8').strip()
        if output == 'true':
            return True
        else:
            return False


def _get_head_commit_id() -> str:
    if _is_in_git_repo():
        res = subprocess.run('git rev-parse --short HEAD', shell=True, capture_output=True)
        if res.returncode == 0:
            return res.stdout.decode('utf8').strip()
        else:
            return ''
    return ''


def initiate(*registries: Registry, logger=False, log_dir=False, log_level=False, gpus=False, random_seed=False, commit_id=False, stacklevel=1):
    """
    This function does a few things.
    1. Hook registries to arglib.
    2. Add a few default arguments: log_dir, log_level, message or random_seed. Note that setting up a random seed is not done by this function since there might be multiple seeds to set up.
    3. Automatically set up log_dir if not already specified and mkdir.
    4. Create a logger with proper log_level and file_path.
    5. Add the current head commit id.
    """
    if registries:
        for reg in registries:
            add_registry(reg, stacklevel=2)

    stacklevel = stacklevel + 1
    if log_dir:
        add_argument('log_dir', dtype='path', msg='log directory', stacklevel=stacklevel)
        add_argument('message', default='', msg='message to append to the config class name', stacklevel=stacklevel)
    if log_level:
        add_argument('log_level', default='INFO', msg='log level', stacklevel=stacklevel)
    if gpus:
        add_argument('gpus', dtype=int, nargs='+', msg='GPUs to use', stacklevel=stacklevel)
    if random_seed:
        add_argument('random_seed', dtype=int, default=1234, msg='random seed to set', stacklevel=stacklevel)
    if commit_id:
        commit_id = _get_head_commit_id()
        add_argument('commit_id', dtype=str, default=commit_id,
                     msg='commit id of current head, automatically computed', stacklevel=stacklevel)
    parse_args(known_only=True)

    # Set an environment variable.
    if gpus and g.gpus:
        # NOTE(j_luo) This environment variable is a string.
        os.environ['CUDA_VISIBLE_DEVICES'] = ','.join(map(str, g.gpus))

    # log_dir would be automatically set as follows if it is not specified manually:
    # ./log/<date>/<config_class_name>[-<message>]/<timestamp>
    if log_dir and not g.log_dir:
        folder = Path('./log')
        configs = get_configs()
        identifier = '-'.join(filter(lambda x: x is not None, configs.values()))
        identifier = identifier or 'default'
        if g.message:
            identifier += f'-{g.message}'

        while True:
            now = datetime.now()
            date = now.strftime(r"%Y-%m-%d")
            timestamp = now.strftime(r"%H-%M-%S")
            log_dir = folder / date / identifier / timestamp
            if log_dir.exists():
                time.sleep(1)
            else:
                set_argument('log_dir', log_dir, _force=True)
                log_dir.mkdir(parents=True)
                break

    # Create a logger.
    if logger:
        file_path = Path(g.log_dir) / 'log' if log_dir else None
        log_level = g.log_level if log_level else 'INFO'
        create_logger(file_path=file_path, log_level=log_level)
