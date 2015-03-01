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
# Author: Iban Eguia <iban.eguia@opendeusto.es>
#

import weblab.experiment.experiment as Experiment

from voodoo.override import Override
from voodoo.log import logged

import urllib2
import json
import random
import sqlite3
import time

# Actually defined through the configuration.
DEBUG = None
ROMIE_SERVER = "http://192.168.0.190:8000/"

class RoMIExperiment(Experiment.Experiment):

	def __init__(self, coord_address, locator, cfg_manager, *args, **kwargs):
		super(RoMIExperiment, self).__init__(*args, **kwargs)
		self._cfg_manager = cfg_manager
		self.read_base_config()

	def read_base_config(self):
		"""
		Reads the base config parameters from the config file.
		"""

		self.database = self._cfg_manager.get_value('romie_sqlite')

	@Override(Experiment.Experiment)
	@logged("info")
	def do_get_api(self):
		return "2"

	@Override(Experiment.Experiment)
	@logged("info")
	def do_start_experiment(self, client_initial_data, server_initial_data):
		"""
		Callback run when the experiment is started.
		"""
		if(DEBUG):
			print "[RoMIE] do_start_experiment called"

		data = json.loads(server_initial_data)
		self.username = data['request.username']
		self.questions = self._cfg_manager.get_value('questions')
		self.question = {}
		self.q_difficulty = 0
		self.points = 0
		self.last_tag = ''
		self.finish_time = 0

		return ""

	@Override(Experiment.Experiment)
	@logged("info")
	def do_send_command_to_device(self, command):
		"""
		Callback run when the client sends a command to the experiment
		@param command Command sent by the client, as a string.
		"""
		if(DEBUG):
			print "[RoMIE] Command received: %s" % command

		global ROMIE_SERVER

		if command == 'F':
			tag = urllib2.urlopen("%sf" % ROMIE_SERVER).read()
			if tag.startswith('Tag') and tag != self.last_tag:

				self.last_tag = tag

				self.q_difficulty = int(self.points/100)
				if self.q_difficulty > 10:
					self.q_difficulty = 10

				index = random.randint(0, len(self.questions[self.q_difficulty])-1)
				self.question = self.questions[self.q_difficulty][index]

				response_question = {
					'question': self.question['question'],
					'answers': self.question['answers']
				}

				return json.dumps(response_question)
			else:
				return 'OK'
		elif command == 'L':
			return urllib2.urlopen("%sl" % ROMIE_SERVER).read()
		elif command == 'R':
			return urllib2.urlopen("%sr" % ROMIE_SERVER).read()
		elif command.startswith("ANSWER"):

			response = int(command.split()[1])
			correct = self.question['correct'] == response

			if correct:
				self.points += self.question['points']
				self.finish_time += self.question['time']
				self.update_points()
				self.questions[self.q_difficulty].remove(self.question)
				self.question = {}

			return json.dumps({"correct": correct, "points": self.points, "finish_time": self.finish_time})

		elif command == 'CHECK_REGISTER':
			conn = sqlite3.connect(self.database)
			cur = conn.cursor()

			cur.execute("SELECT COUNT(*) FROM forotech WHERE username = ?", (self.username,));
			count = cur.fetchone()[0]

			result = ''
			if count == 0:
				result = 'REGISTER'
			else:
				self.update_points()
				self.finish_time = round(time.time()+self._cfg_manager.get_value('romie_time'), 3)
				result = self.finish_time

			conn.close()

			return result

		elif command.startswith('REGISTER'):
			data = json.loads(command.split(' ', 1)[1])

			conn = sqlite3.connect(self.database)
			conn.execute("INSERT INTO forotech values (?,?,?,?,?,?,?)",
				(self.username, data["name"], data["surname"], data["school"], data["bdate"], data["email"], 0,))
			conn.commit()
			conn.close()

			self.finish_time = round(time.time()+self._cfg_manager.get_value('romie_time'), 3)

			return self.finish_time

		elif command == 'FINISH':

			conn = sqlite3.connect(self.database)
			conn.execute("UPDATE forotech SET points = ? WHERE username = ?", (self.points, self.username,))

			cur = conn.cursor()
			cur.execute("SELECT username, name, surname, school, points FROM forotech ORDER BY points DESC LIMIT 10")
			result = cur.fetchall()
			ranking = list()

			for user in result:
				current = (user[0] == self.username)
				ranking.append({"name":user[1], "surname":user[2], "school":user[3], "points":user[4], "current":current})

			conn.commit()
			conn.close()
			return json.dumps(ranking)

		return "ERROR"

	@Override(Experiment.Experiment)
	@logged("info")
	def do_dispose(self):
		"""
		Callback to perform cleaning after the experiment ends.
		"""
		if(DEBUG):
			print "[RoMIE] do_dispose called"

		return "OK"

	def update_points(self):
		"""
		Add points in the database
		"""
		conn = sqlite3.connect(self.database)
		conn.execute("UPDATE forotech SET points = ? WHERE username = ?", (self.points, self.username,))
		conn.commit()
		conn.close()
