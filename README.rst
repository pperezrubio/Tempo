=====
tempo
=====

Description
===========

`tempo` is a lightweight cron-as-a-service implementation. It consists of two
components, the `tempo-api` which is a webserver that exposes a RESTful
webservice for adding and removing cron-jobs, and `tempo-worker` which is
responsible for performing the actual task.


How It Works
============

1. `tempo-api` receives a request to create a new cron task, writes task to the
   DB, then updates its crontab to fire off the cron job at the appropriate
   time.
2. When the designated time is reached, cron will execute `tempo-enqueue`
   which will add a new task to the `tempo` task queue.
3. `tempo-worker` will pull jobs from this task queue and then execute
   the requested action. Actions are functions defined in the `tempo.actions`
   module.


Usage
=====

1. Start the `tempo-api` on a machine::

       tempo-api

2. On a machine that will act as the worker, source the novarc for worker::

       . novarc

   This is needed because many of the actions that the `tempo-worker`
   will run will ultimatly shell out to a python-novalcient command.

3. On that same machine, Start the `tempo-worker`::

        tempo-worker
