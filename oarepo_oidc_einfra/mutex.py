#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# oarepo-oidc-einfra  is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""
An implementation of a mutex over the cache. Note: if you have multiple redis caches,
you need to implement a distributed lock instead of this simple implementation to have
a mutex that works in all cases of disaster scenarios.
"""
import functools
import secrets
import threading
import time
from random import random

from invenio_cache import current_cache


class CacheMutex:
    """
    A simple mutex implementation using the cache.

    Because propagation from master cache server to slaves might be asynchronous and
    messages might be lost in case when master responds before the slave is updated,
    this mutex is not reliable in case of a disaster.

    To be able to handle these cases, you would need connection both to the master and
    slaves and implement a distributed lock such as Redlock algorithm for redis.
    """

    def __init__(self, key, timeout=3600, tries=10, wait_time=120):
        """Creates the mutex.

        :param key: The key inside cache where the mutex data are stored.
        :param timeout: The mutex will be released automatically after this time.
        :param tries: The number of tries to acquire the lock if it is locked.
        :param wait_time: The time to wait between the tries.

        Usage:

        with CacheMutex("my-mutex-key"):
            # do something that needs to be protected by the mutex
        """
        self.key = key
        self.value = secrets.token_hex(32)
        self.timeout = timeout
        self.tries = tries
        self.wait_time = wait_time

    def __enter__(self):
        """Acquires the mutex."""
        for k in range(self.tries):
            if current_cache.cache.add(self.key, self.value, timeout=self.timeout):
                # sanity check
                if current_cache.cache.get(self.key) != self.value:
                    continue
                return
            # add random to desynchronize
            time.sleep(self.wait_time * 0.9 + self.wait_time * 0.1 * random())
        raise ValueError(
            f"Could not acquire mutex for {self.tries} times, "
            f"waiting {self.wait_time} seconds each time"
        )

    def __exit__(self, exc_type, exc_value, traceback):
        """Releases the mutex."""
        if current_cache.cache.get(self.key) == self.value:
            current_cache.cache.delete(self.key)


mutex_thread_local = threading.local()
"""make the mutex below reentrant within the same thread"""


def mutex(key, timeout=3600, tries=10, wait_time=120):
    """
    A decorator that creates a mutex for a function.

    :param key: The key inside cache where the mutex data are stored.
    :param timeout: The mutex will be released automatically after this time.
    :param tries: The number of tries to acquire the lock if it is locked.
    :param wait_time: The time to wait between the tries.

    Within the same thread, the mutex with the same key is re-entrant.

    Usage:

    @mutex("my-mutex-key")
    def my_function():
        # do something that needs to be protected by the mutex
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(mutex_thread_local, key):
                setattr(mutex_thread_local, key, True)
                try:
                    with CacheMutex(key, timeout, tries, wait_time):
                        return func(*args, **kwargs)
                finally:
                    delattr(mutex_thread_local, key)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator
