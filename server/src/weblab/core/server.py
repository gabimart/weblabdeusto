#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005 onwards University of Deusto
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# This software consists of contributions made by many individuals,
# listed below:
#
# Author: Pablo Orduña <pablo@ordunya.com>
#         Jaime Irurzun <jaime.irurzun@gmail.com>
#

import os
import sys
import uuid
import time
import threading
import urlparse

import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, Blueprint, request, escape

from functools import wraps

import weblab.configuration_doc as configuration_doc

import voodoo.log as log
import voodoo.counter as counter
from voodoo.sessions.session_id import SessionId
from weblab.data.experiments import ExperimentId
from weblab.data.command import Command

from weblab.core.login.manager import LoginManager
from weblab.core.wsgi_manager import WebLabWsgiServer

import weblab.core.reservations as Reservation
import weblab.core.data_retriever as TemporalInformationRetriever
import weblab.core.user_processor as UserProcessor
from weblab.core.reservation_processor import ReservationProcessor
import weblab.core.alive_users as AliveUsersCollection
from weblab.core.coordinator.gateway import create as coordinator_create
import weblab.core.coordinator.store as TemporalInformationStore
from weblab.core.db import DatabaseGateway
import weblab.core.coordinator.status as WebLabSchedulingStatus

import weblab.core.exc as coreExc
import weblab.core.web as web
assert web is not None # Avoid warnings

from voodoo.threaded import threaded

from voodoo.sessions.exc import SessionNotFoundError
import voodoo.sessions.manager as SessionManager
import voodoo.sessions.session_type as SessionType

import voodoo.resources_manager as ResourceManager

from weblab.admin.web.app import AdministrationApplication

check_session_params = dict(
        exception_to_raise = coreExc.SessionNotFoundError,
        what_session       = "Core Users ",
        cut_session_id     = ';'
    )

check_reservation_session_params = dict(
        exception_to_raise         = coreExc.SessionNotFoundError,
        what_session               = "Core Reservations ",
        session_manager_field_name = "_reservations_session_manager",
        cut_session_id             = ';'
    )

_resource_manager = ResourceManager.CancelAndJoinResourceManager("UserProcessingServer")

CHECKING_TIME_NAME    = 'core_checking_time'
DEFAULT_CHECKING_TIME = 3 # seconds

WEBLAB_CORE_SERVER_SESSION_POOL_ID              = "core_session_pool_id"
WEBLAB_CORE_SERVER_RESERVATIONS_SESSION_POOL_ID = "core_session_pool_id"
WEBLAB_CORE_SERVER_CLEAN_COORDINATOR            = "core_coordinator_clean"

# This could be refactored so the first time it's called weblab_api.user_processor, it is generated, and if it's been generated in the context, it is also removed (update_latest_timestamp) on the wrap_func()
# Alternatively, we could remove the user_processors (which indeed makes more sense)
def load_user_processor(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        server = weblab_api.ctx.server_instance
        session_id = SessionId(weblab_api.ctx.session_id)
        try:
            session = server._session_manager.get_session_locking(session_id)
        except SessionNotFoundError:
            raise coreExc.SessionNotFoundError("Core Users session not found")

        try:
            weblab_api.ctx.user_session = session
            weblab_api.ctx.user_processor = server._load_user(session)
            try:
                return func(*args, **kwargs)
            finally:
                weblab_api.ctx.user_processor.update_latest_timestamp()
        finally:
            server._session_manager.modify_session_unlocking(session_id, session)

    return wrapper

def load_reservation_processor(func):
    """decorator that loads the reservation_processor given the reservation_id"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        server = weblab_api.ctx.server_instance
        reservation_id = SessionId(weblab_api.ctx.reservation_id.split(';')[0])
        try:
            session = server._reservations_session_manager.get_session_locking(reservation_id)
        except SessionNotFoundError:
            raise coreExc.SessionNotFoundError("Core Reservations session not found")

        try:
            weblab_api.ctx.reservation_session = session
            weblab_api.ctx.reservation_processor = server._load_reservation(session)
            try:
                return func(*args, **kwargs)
            finally:
                weblab_api.ctx.reservation_processor.update_latest_timestamp()
        finally:
            server._reservations_session_manager.modify_session_unlocking(reservation_id, session)

    return wrapper

from weblab.core.wl import weblab_api

# TODO:
# - Update session id
# - REST API CSRF

# >>> requests.post("http://localhost/weblab/administration/", data = json.dumps({'method' : 'login', 'params' : { 'username' : 'any', 'password' : 'password'}})).text

# 
# 
#  Login methods
# 
# 
@weblab_api.route_api('/login/', dont_log = (('password', 1), ))
def login(username = None, password = None):
    if username is None:
        if request.method == 'GET':
            username = request.args.get('username')
            password = request.args.get('password')
    session_id = weblab_api.ctx.server_instance._login_manager.login(username, password)
    weblab_api.ctx.session_id = session_id.id
    return session_id

@weblab_api.route_api('/login/external/<system>/', methods = [ 'POST'])
def extensible_login(system, credentials = None):
    return weblab_api.ctx.server_instance._login_manager.extensible_login(system, credentials)

@weblab_api.route_api('/login/external/<system>/grant/', methods = [ 'POST' ])
def grant_external_credentials(username = None, password = None, system = None, credentials = None):
    return weblab_api.ctx.server_instance._login_manager.grant_external_credentials(username, password, system, credentials)

@weblab_api.route_api('/login/external/create/create/', methods = [ 'POST' ])
def create_external_user(system = None, credentials = None):
    return weblab_api.ctx.server_instance._login_manager.create_external_user(system, credentials)


# 
# User operations
# 
@weblab_api.route_api('/user/experiments/')
@load_user_processor
def list_experiments():
    return weblab_api.ctx.user_processor.list_experiments()

@weblab_api.route_api('/user/info/')
@load_user_processor
def get_user_information():
    user_information = weblab_api.ctx.user_processor.get_user_information()
    if weblab_api.ctx.user_processor.is_admin():
        admin_url = weblab_api.ctx.core_server_url + "administration/admin/"

        try:
            user_information.admin_url = urlparse.urlparse(admin_url).path
        except:
            user_information.admin_url = admin_url
    else:
        user_information.admin_url = ""

    if weblab_api.ctx.user_processor.is_instructor():
        instructor_url = weblab_api.ctx.core_server_url + "administration/instructor/"
        try:
            user_information.instructor_url = urlparse.urlparse(instructor_url).path
        except:
            user_information.instructor_url = instructor_url
    else:
        user_information.instructor_url = ""

    return user_information

@weblab_api.route_api('/user/reservation_id/')
@load_user_processor
def get_reservation_id_by_session_id():
    return weblab_api.ctx.user_session.get('reservation_id')

@weblab_api.route_api('/user/reservation/<reservation_id>/')
@load_user_processor
def get_experiment_use_by_id(reservation_id = None):
    return weblab_api.ctx.user_processor.get_experiment_use_by_id(SessionId(reservation_id['id']))

@weblab_api.route_api('/user/reservations/<reservation_ids>/')
@load_user_processor
def get_experiment_uses_by_id(reservation_ids = None):
    if isinstance(reservation_ids, basestring):
        reservation_ids = [ {'id' : reservation_id} for reservation_id in reservation_ids.split(',') ]
    return weblab_api.ctx.user_processor.get_experiment_uses_by_id([ SessionId(reservation_id['id']) for reservation_id in reservation_ids ])

@weblab_api.route_api('/user/permissions/')
@load_user_processor
def get_user_permissions():
    return weblab_api.ctx.user_processor.get_user_permissions()

@weblab_api.route_api('/user/reservations/', methods = [ 'POST' ])
@load_user_processor
def reserve_experiment(experiment_id = None, client_initial_data = None, consumer_data = None):
    server = weblab_api.ctx.server_instance
    client_address = weblab_api.ctx.client_address
    # core_server_universal_id should be copied
    experiment_id = ExperimentId(experiment_id['exp_name'], experiment_id['cat_name'])
    status = weblab_api.ctx.user_processor.reserve_experiment( experiment_id, client_initial_data, consumer_data, client_address, server.core_server_universal_id)

    if status == 'replicated':
        return Reservation.NullReservation()

    reservation_id         = status.reservation_id.split(';')[0]
    reservation_session_id = SessionId(reservation_id)

    server._alive_users_collection.add_user(reservation_session_id)

    session_id = server._reservations_session_manager.create_session(reservation_id)

    initial_session = {
                    'session_polling'    : (time.time(), ReservationProcessor.EXPIRATION_TIME_NOT_SET),
                    'latest_timestamp'   : 0,
                    'experiment_id'      : experiment_id,
                    'creator_session_id' : weblab_api.ctx.user_session['session_id'], # Useful for monitor; should not be used
                    'reservation_id'     : reservation_session_id,
                    'federated'          : False,
                }
    reservation_processor = server._load_reservation(initial_session)
    reservation_processor.update_latest_timestamp()

    if status.status == WebLabSchedulingStatus.WebLabSchedulingStatus.RESERVED_LOCAL:
        reservation_processor.process_reserved_status(status)

    if status.status == WebLabSchedulingStatus.WebLabSchedulingStatus.RESERVED_REMOTE:
        reservation_processor.process_reserved_remote_status(status)

    server._reservations_session_manager.modify_session(session_id, initial_session)
    return Reservation.Reservation.translate_reservation( status )

@weblab_api.route_api('/user/logout/', methods = ['POST'])
def logout():
    server_instance = weblab_api.ctx.server_instance
    session_id = SessionId(weblab_api.ctx.session_id)

    if server_instance._session_manager.has_session(session_id):
        session        = server_instance._session_manager.get_session(session_id)

        user_processor = server_instance._load_user(session)

        reservation_id = session.get('reservation_id')
        if reservation_id is not None and not user_processor.is_access_forward_enabled():
            #
            # If "is_access_forward_enabled", the user (or more commonly, entity) can log out without
            # finishing his current reservation
            #
            # Furthermore, whenever booking is supported, this whole idea should be taken out. Even
            # with queues it might not make sense, depending on the particular type of experiment.
            #
            reservation_session = server_instance._reservations_session_manager.get_session(SessionId(reservation_id))
            reservation_processor = server_instance._load_reservation(reservation_session)
            reservation_processor.finish()
            server_instance._alive_users_collection.remove_user(reservation_id)

        user_processor.logout()
        user_processor.update_latest_timestamp()

        server_instance._session_manager.delete_session(session_id)
        return {}
    else:
        raise coreExc.SessionNotFoundError( "User Processing Server session not found")


#
#
# Reservation operations
#
# 

@weblab_api.route_api('/reservation/finish/', methods = ['POST'])
@load_reservation_processor
def finished_experiment():
    reservation_session_id = weblab_api.ctx.reservation_processor.get_reservation_session_id()
    weblab_api.ctx.server_instance._alive_users_collection.remove_user(reservation_session_id)
    return weblab_api.ctx.reservation_processor.finish()

@weblab_api.route_api('/reservation/file/', methods = ['POST'], dont_log = (('file_content', 0),))
@load_reservation_processor
def send_file(file_content = None, file_info = None):
    """ send_file(file_content, file_info)

    Sends file to the experiment.
    """
    reservation_processor = weblab_api.ctx.reservation_processor
    weblab_api.ctx.server_instance._check_reservation_not_expired_and_poll( reservation_processor )
    return reservation_processor.send_file( file_content, file_info )

@weblab_api.route_api('/reservation/command/', methods = ['POST'])
@load_reservation_processor
def send_command(command):
    """ send_command(command)

    send_command sends an abstract string <command> which will be unpacked by the
    experiment.
    """
    reservation_processor = weblab_api.ctx.reservation_processor
    weblab_api.ctx.server_instance._check_reservation_not_expired_and_poll( reservation_processor )
    return reservation_processor.send_command( Command(command['commandstring']) )

@weblab_api.route_api('/reservation/file/async/', methods = ['POST'], dont_log = (('file_content', 0),))
@load_reservation_processor
def send_async_file(file_content, file_info):
    """
    send_async_file(session_id, file_content, file_info)
    Sends a file asynchronously to the experiment. The response
    will not be the real one, but rather, a request_id identifying
    the asynchronous query.
    @param session Session
    @param file_content Contents of the file.
    @param file_info File information of the file.
    @see check_async_command_status
    """
    reservation_processor = weblab_api.ctx.reservation_processor
    weblab_api.ctx.server_instance._check_reservation_not_expired_and_poll( reservation_processor )
    return reservation_processor.send_async_file( file_content, file_info )

# TODO: This method should now be finished. Will need to be verified, though.
@weblab_api.route_api('/reservation/file/async/status')
@load_reservation_processor
def check_async_command_status(request_identifiers):
    """
    check_async_command_status(session_id, request_identifiers)
    Checks the status of several asynchronous commands.

    @param session: Session id
    @param request_identifiers: A list of the request identifiers of the
    requests to check.
    @return: Dictionary by request-id of the tuples: (status, content)
    """
    reservation_processor = weblab_api.ctx.reservation_processor
    weblab_api.ctx.server_instance._check_reservation_not_expired_and_poll( reservation_processor )
    return reservation_processor.check_async_command_status( request_identifiers )

@weblab_api.route_api('/reservation/command/async/', methods = ['POST'])
@load_reservation_processor
def send_async_command(command):
    """
    send_async_command(session_id, command)

    send_async_command sends an abstract string <command> which will be unpacked by the
    experiment, and run asynchronously on its own thread. Its status may be checked through
    check_async_command_status.
    """
    reservation_processor = weblab_api.ctx.reservation_processor
    weblab_api.ctx.server_instance._check_reservation_not_expired_and_poll( reservation_processor )
    return reservation_processor.send_async_command( Command(command['commandstring']) )

@weblab_api.route_api('/reservation/info/')
@load_reservation_processor
def get_reservation_info():
    return weblab_api.ctx.reservation_processor.get_info()


@weblab_api.route_api('/reservation/poll/')
@load_reservation_processor
def poll():
    reservation_processor = weblab_api.ctx.reservation_processor
    return weblab_api.ctx.server_instance._check_reservation_not_expired_and_poll( reservation_processor )

@weblab_api.route_api('/reservation/status/', max_log_size = 1000)
@load_reservation_processor
def get_reservation_status():
    reservation_processor = weblab_api.ctx.reservation_processor
    weblab_api.ctx.server_instance._check_reservation_not_expired_and_poll( reservation_processor, False )
    return reservation_processor.get_status()

class WebLabFlaskServer(WebLabWsgiServer):
    def __init__(self, server, cfg_manager):
        core_server_url  = cfg_manager.get_value( 'core_server_url', '' )
        self.script_name = urlparse.urlparse(core_server_url).path.split('/weblab')[0] or ''

        self.app = Flask('weblab.core.wl')
        self.app.config['SECRET_KEY'] = os.urandom(32)
        self.app.config['APPLICATION_ROOT'] = self.script_name
        self.app.config['SESSION_COOKIE_PATH'] = self.script_name + '/weblab/'
        self.app.config['SESSION_COOKIE_NAME'] = 'weblabsession'

        # Mostly for debugging purposes, this snippet will print the site-map so that we can check
        # which methods we are routing.
        @self.app.route("/site-map")
        def site_map():
            lines = []
            for rule in self.app.url_map.iter_rules():
                line = str(escape(repr(rule)))
                lines.append(line)

            ret = "<br>".join(lines)
            return ret


        flask_debug = cfg_manager.get_value('flask_debug', False)
        if flask_debug:
            print >> sys.stderr, "*" * 50
            print >> sys.stderr, "WARNING " * 5
            print >> sys.stderr, "flask_debug is set to True. This is an important security leak. Do not use it in production, only for bugfixing!!!"
            print >> sys.stderr, "WARNING " * 5
            print >> sys.stderr, "*" * 50
        self.app.config['DEBUG'] = flask_debug
        if os.path.exists('logs'):
            f = os.path.join('logs','admin_app.log')
        else:
            f = 'admin_app.log'
        file_handler = RotatingFileHandler(f, maxBytes = 50 * 1024 * 1024)
        file_handler.setLevel(logging.WARNING)
        self.app.logger.addHandler(file_handler)

        super(WebLabFlaskServer, self).__init__(cfg_manager, self.app)

        json_api = Blueprint('json', __name__)
        weblab_api.apply_routes_api(json_api, server)
        self.app.register_blueprint(json_api, url_prefix = '/weblab/json')
        self.app.register_blueprint(json_api, url_prefix = '/weblab/login/json')
 
        authn_web = Blueprint('login_web', __name__)
        weblab_api.apply_routes_login_web(authn_web, server)
        self.app.register_blueprint(authn_web, url_prefix = '/weblab/login/web')

        core_web = Blueprint('core_web', __name__)
        weblab_api.apply_routes_web(core_web, server)
        self.app.register_blueprint(core_web, url_prefix = '/weblab/web')
       
        self.admin_app = AdministrationApplication(self.app, cfg_manager, server)

class UserProcessingServer(object):
    """
    The UserProcessingServer will receive client requests, which will be forwarded
    to an appropriate UserProcessor for the specified session identifier.
    """

    def __init__(self, coord_address, locator, cfg_manager, dont_start = False, *args, **kwargs):
        super(UserProcessingServer,self).__init__(*args, **kwargs)

        log.log( UserProcessingServer, log.level.Info, "Starting Core Server...")

        self._stopping = False
        self._cfg_manager    = cfg_manager
        self.config          = cfg_manager
        self._locator        = locator

        self.core_server_url = cfg_manager.get_doc_value(configuration_doc.CORE_SERVER_URL)

        if cfg_manager.get_value(configuration_doc.CORE_UNIVERSAL_IDENTIFIER, 'default') == 'default' or cfg_manager.get_value(configuration_doc.CORE_UNIVERSAL_IDENTIFIER_HUMAN, 'default') == 'default':
            generated = uuid.uuid1()
            msg = "Property %(property)s or %(property_human)s not configured. Please establish: %(property)s = '%(uuid)s' and %(property_human)s = 'server at university X'. Otherwise, when federating the experiment it could enter in an endless loop." % {
                'property'       : configuration_doc.CORE_UNIVERSAL_IDENTIFIER,
                'property_human' : configuration_doc.CORE_UNIVERSAL_IDENTIFIER_HUMAN,
                'uuid'           : generated
            }
            print msg
            print >> sys.stderr, msg
            log.log( UserProcessingServer, log.level.Error, msg)

        self.core_server_universal_id       = cfg_manager.get_doc_value(configuration_doc.CORE_UNIVERSAL_IDENTIFIER)
        self.core_server_universal_id_human = cfg_manager.get_doc_value(configuration_doc.CORE_UNIVERSAL_IDENTIFIER_HUMAN)

        #
        # Create session managers
        #

        session_type_str    = cfg_manager.get_doc_value(configuration_doc.WEBLAB_CORE_SERVER_SESSION_TYPE)
        if not hasattr(SessionType, session_type_str):
            raise coreExc.NotASessionTypeError( 'Not a session type: %s' % session_type_str )
        session_type = getattr(SessionType, session_type_str)

        session_pool_id       = cfg_manager.get_doc_value(configuration_doc.WEBLAB_CORE_SERVER_SESSION_POOL_ID)
        self._session_manager = SessionManager.SessionManager( cfg_manager, session_type, session_pool_id )

        reservations_session_pool_id = cfg_manager.get_value(WEBLAB_CORE_SERVER_RESERVATIONS_SESSION_POOL_ID, "CoreServerReservations")
        self._reservations_session_manager = SessionManager.SessionManager( cfg_manager, session_type, reservations_session_pool_id )

        #
        # Coordination
        #

        coordinator_implementation = cfg_manager.get_doc_value(configuration_doc.COORDINATOR_IMPL)
        self._coordinator    = coordinator_create(coordinator_implementation, self._locator, cfg_manager)

        #
        # Database and information storage managers
        #

        self._db_manager     = DatabaseGateway(cfg_manager)

        self._commands_store = TemporalInformationStore.CommandsTemporalInformationStore()

        self._temporal_information_retriever = TemporalInformationRetriever.TemporalInformationRetriever(cfg_manager, self._coordinator.initial_store, self._coordinator.finished_store, self._commands_store, self._coordinator.completed_store, self._db_manager)
        self._temporal_information_retriever.start()

        #
        # Alive users
        #

        self._alive_users_collection = AliveUsersCollection.AliveUsersCollection(
                self._locator, self._cfg_manager, session_type, self._reservations_session_manager, self._coordinator, self._commands_store, self._coordinator.finished_reservations_store)

        # Login Manager
        self._login_manager  = LoginManager(self._db_manager, self)

        #
        # Initialize facade (comm) servers
        #

        self._server_route   = cfg_manager.get_doc_value(configuration_doc.CORE_FACADE_SERVER_ROUTE)

        self.flask_server = WebLabFlaskServer(self, cfg_manager)

        self.dont_start = cfg_manager.get_value('dont_start', dont_start)
        if not self.dont_start:
            self.flask_server.start()

        self.app = self.flask_server.app

        #
        # Start checking times
        #
        checking_time = self._cfg_manager.get_value(CHECKING_TIME_NAME, DEFAULT_CHECKING_TIME)
        timer = threading.Timer(checking_time, self._renew_checker_timer)
        timer.setName(counter.next_name("ups-checker-timer"))
        timer.setDaemon(True)
        timer.start()
        _resource_manager.add_resource(timer)



    def stop(self):
        """ Stops all the servers and threads """
        self._stopping = True

        self._temporal_information_retriever.stop()
        self._coordinator.stop()

        if hasattr(super(UserProcessingServer, self), 'stop'):
            super(UserProcessingServer, self).stop()

        if not self.dont_start:
            self.flask_server.stop()

    def _load_user(self, session):
        return UserProcessor.UserProcessor(self._locator, session, self._cfg_manager, self._coordinator, self._db_manager, self._commands_store)

    def _load_reservation(self, session):
        reservation_id = session['reservation_id']
        return ReservationProcessor(self._cfg_manager, reservation_id, session, self._coordinator, self._locator, self._commands_store)

    def _check_reservation_not_expired_and_poll(self, reservation_processor, check_expired = True):
        if check_expired and reservation_processor.is_expired():
            reservation_processor.finish()
            reservation_id = reservation_processor.get_reservation_id()
            raise coreExc.NoCurrentReservationError( 'Current user (identified by reservation %r) does not have any experiment assigned' % reservation_id )

        try:
            reservation_processor.poll()
        except coreExc.NoCurrentReservationError:
            if check_expired:
                raise
        reservation_processor.update_latest_timestamp()
        # It's already locked, we just update that this user is still among us
        self._reservations_session_manager.modify_session(
                reservation_processor.get_reservation_session_id(),
                reservation_processor.get_session()
            )

    @threaded(_resource_manager)
    def _purge_expired_users(self, expired_users):
        for expired_reservation in expired_users:
            if self._stopping:
                return
            try:
                expired_session = self._reservations_session_manager.get_session_locking(expired_reservation)
                try:
                    reservation_processor = self._load_reservation(expired_session)
                    reservation_processor.finish()
                finally:
                    self._reservations_session_manager.modify_session_unlocking(expired_reservation, expired_session)
            except Exception as e:
                log.log( UserProcessingServer, log.level.Error,
                    "Exception freeing experiment of %s: %s" % (expired_reservation, e))
                log.log_exc( UserProcessingServer, log.level.Warning)

    def _renew_checker_timer(self):
        checking_time = self._cfg_manager.get_value(CHECKING_TIME_NAME, DEFAULT_CHECKING_TIME)
        while not self._stopping:
            expired_users = self._alive_users_collection.check_expired_users()
            if len(expired_users) > 0:
                self._purge_expired_users(expired_users)

            time.sleep(checking_time)

    # # # # # # # # # # # #
    # Session operations  #
    # # # # # # # # # # # #

    def _reserve_session(self, db_session_id):
        session_id = self._session_manager.create_session()
        initial_session = {
            'db_session_id'       : db_session_id,
            'session_id'          : session_id,
            'latest_timestamp'    : 0 # epoch
        }
        user_processor = self._load_user(initial_session)
        user_processor.get_user_information()
        user_processor.update_latest_timestamp()
        self._session_manager.modify_session(session_id,initial_session)
        return session_id, self._server_route

