#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2009 University of Deusto
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# This software consists of contributions made by many individuals, 
# listed below:
#
# Author: Pablo Orduña <pablo@ordunya.com>
# 
import weblab.experiment.exc as ExperimentExceptions

import threading
import weblab.core.coordinator.Coordinator as Coordinator
import json

class Experiment(object):

    def __init__(self, *args, **kwargs):
        super(Experiment, self).__init__(*args, **kwargs)
        
        # We save the main thread's identifier so that we can easily know
        # from the experiments whether a command is being executed from it
        # (and hence synchronously) or from a different thread (and hence
        # asynchronously).
        self._thread_ident = threading.currentThread().getName()
        
    def _is_main_thread(self):
        """
        Checks whether the caller's thread is the main experiment thread.
        If it isn't, we can assume that the particular request is being
        executed asynchronously, from a different thread.
        """
        return self._thread_ident == threading.currentThread().getName()

    def do_start_experiment(self, client_initial_data, server_initial_data):
        # Default implementation: empty
        pass

    def do_send_file_to_device(self, file_content, file_info):
        """do_send_file_to_device(file_content, file_info)
        raises (FeatureNotImplemented, SendingFileFailureException)
        """
        raise ExperimentExceptions.FeatureNotImplementedException(
                "send_file_to_device has not been implemented in this experiment"
            )

    def do_send_command_to_device(self, command):
        """do_send_command_to_device(command)
        raises (FeatureNotImplemented, SendingCommandFailureException)
        """
        raise ExperimentExceptions.FeatureNotImplementedException(
                "send_command_to_device has not been implemented in this experiment"
            )

    def do_should_experiment_finish(self):
        # 
        # Should the experiment finish? If the experiment server should be able to
        # say "I've finished", it will be asked every few time; if the experiment
        # is completely interactive (so it's up to the user and the permissions of
        # the user to say when the session should finish), it will never be asked.
        # 
        # Therefore, this method will return a numeric result, being:
        #   - result > 0: it hasn't finished but ask within result seconds.
        #   - result == 0: completely interactive, don't ask again
        #   - result == -1: it has finished.
        # 
        return 0

    def do_dispose(self):
        # 
        # Default implementation: yes, I have finished.
        # 
        return json.dumps({ Coordinator.FINISH_FINISHED_MESSAGE : True, Coordinator.FINISH_DATA_MESSAGE : ""})

    def do_is_up_and_running(self):
        # 
        # Is the experiment up and running?
        # 
        # The scheduling system will ensure that the experiment will not be
        # assigned to other student while this method is called. The result
        # is an array of integer + String, where the first argument is:
        # 
        #   - result >= 0: "the experiment is OK; please check again 
        #                  within $result seconds"
        #   - result == 0: the experiment is OK and I can't perform a proper
        #                  estimation
        #   - result == -1: "the experiment is broken"
        # 
        # And the second (String) argument is the message detailing while 
        # it failed
        # 
        return (600, '') # Default value: check every 10 minutes
