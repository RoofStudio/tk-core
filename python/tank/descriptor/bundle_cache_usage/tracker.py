# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import threading
import Queue

from ...import LogManager
from .errors import BundleCacheTrackingTimeoutError
from .database import BundleCacheUsageDatabase as BundleCacheUsageDatabase


log = LogManager.get_logger(__name__)


class BundleCacheUsageTracker(threading.Thread):

    """
    Update bundle cache usage in a simple single table database.
    To minimize performance impact, usage is logged using a
    fire-and-forget scheme to a worker thread.

    .. References::

        https://docs.python.org/2/library/queue.html
        https://docs.python.org/2/library/threading.html
    """

    DEFAULT_STOP_TIMEOUT = 10 # in seconds

    KEY_BUNDLE_COUNT = "bundle_count"
    KEY_LAST_USAGE_DATE = "last_usage_date"
    KEY_USAGE_COUNT = "usage_count"

    # keeps track of the single instance of the class
    __singleton_lock = threading.Lock()
    __singleton_instance = None

    def __new__(cls, *args, **kwargs):
        #
        # Based on tornado.ioloop.IOLoop.instance() approach.
        #
        # See:
        #   https://github.com/facebook/tornado
        #   https://gist.github.com/werediver/4396488
        #   https://en.wikipedia.org/wiki/Double-checked_locking
        #
        if not cls.__singleton_instance:
            with cls.__singleton_lock:
                if not cls.__singleton_instance:
                    cls.__singleton_instance = super(BundleCacheUsageTracker, cls).__new__(cls, *args, **kwargs)
                    cls.__singleton_instance.__initialized = False

        return cls.__singleton_instance

    def __init__(self):
        super(BundleCacheUsageTracker, self).__init__()
        if (self.__initialized):
            return
        self.__initialized = True
        self._tasks = Queue.Queue()
        self._errors = Queue.Queue()

    @ classmethod
    def delete_instance(cls, timeout=DEFAULT_STOP_TIMEOUT):
        """
        Safely lock the instance, stop the worker thread and set the instance to None
        :param timeout: A float timeout in seconds
        """
        with cls.__singleton_lock:
            if cls.__singleton_instance:
                cls.__singleton_instance.stop(timeout)
                cls.__singleton_instance = None

    #
    # Private methods
    # Running exclusively from the worker thread context
    #
    ###########################################################################

    def __log_error(self, exception, message):
        """
        Helper method that adds an exception and custom message to a queue allowing
        reporting of errors from the worker thread back into the main thread.

        :param exception: A
        :param message: a str custom message
        """
        self._errors.put((exception, message))
        self._errors.task_done()

    def __track_usage(self, bundle_path):
        """
        Update database's last usage date and usage count for the specified entry.

        .. note:: Invoked exclusively from the worker thread.

        :param bundle_path: A str of a bundle path
        """
        database = BundleCacheUsageDatabase()
        database.track_usage(bundle_path)

    def run(self):
        """
        Implementation of threading.Thread.run()
        """

        try:
            while True:

                # Wait (block) until something is added to the queue
                method, args, kwargs = self._tasks.get()
                if method == "QUIT":
                    break

                if method:
                    try:
                        method(*args, **kwargs)

                    except Exception as e:
                        self.__log_error(e, "Unexpected error consuming task")
                    finally:
                        self._tasks.task_done()

        except Exception as e:
            self.__log_error(e, "Unexpected exception in the worker run() method")

    #
    # Protected methods
    # Can run from either threading contextes
    #
    ###########################################################################

    def _check_for_queued_errors(self):
        while not self._errors.empty():
            exception, message = self._errors.get()
            log.error("%s : %s" % (message, exception))

    def _queue_task(self, method, *args, **kwargs):
        """
        Add a task to the worker thread queue.

        .. note:: Called from main thread

        :param method: method to call
        :param args: arguments to pass to the method
        :param kwargs: named arguments to pass to the method
        """
        self._check_for_queued_errors()
        self._tasks.put((method, args, kwargs))

    #
    # Public methods & properties
    # Can run from either threading contextes
    #
    ###########################################################################

    @classmethod
    def track_usage(cls, bundle_path):
        """
        Queue a bundle cache usage database update.

        :param bundle_path: a str bundle path
        """
        with cls.__singleton_lock:
            if cls.__singleton_instance:
                cls.__singleton_instance._queue_task(cls.__singleton_instance.__track_usage, bundle_path)

    @property
    def pending_count(self):
        """
        Returns how many tasks are in the queue, still pending.

        .. note:: Indicative only, with the worker thread running,
        by the time the next instruction is executed the value might
        be already different.

        :return: an integer of the currently still queued tasks count
        """
        return self._tasks.qsize()

    def stop(self, timeout=DEFAULT_STOP_TIMEOUT):
        """
        Request worker thread termination and then wait for thread to finish.

        .. note:: An attempt is made to empty the task queued before exiting the worker thread.

        :param timeout: A float timeout in seconds
        """
        if self.is_alive():
            log.debug("Requesting worker termination ..." )
            self._tasks.put("QUIT")
            self.join(timeout=timeout)
            # As join() always returns None, you must call isAlive() after
            # join() to decide whether a timeout happened
            if self.is_alive():
                raise BundleCacheTrackingTimeoutError("Timeout waiting for worker thread to terminated.")

            log.debug("Worker thread terminated cleanly.")



