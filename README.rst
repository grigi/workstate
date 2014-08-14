=========
WorkState
=========

WorkState is a self-documenting Workflow-event state management system.

.. image:: https://travis-ci.org/grigi/workstate.png
   :target: https://travis-ci.org/grigi/workstate

-----
Usage
-----

A minimal example:

.. code:: python

    from workstate.engine2 import Scope, Engine

    class Chapter(Scope):
        'A chapter'
        initial = 'draft'

        class Transitions:
            def proposed__approved(self):
                'Chapter approved'
                return self.marked

        class Events:
            propose = ['draft__proposed']
            approve = ['proposed__approved']
            reject = ['proposed__draft']
            cancel = ['*__canceled']

        class Triggers:
            @trigger('reject', ['proposed'])
            def check_complete(self):
                'Rejects chapter if not complete when landing at proposed state'
                return not self.complete

    class Book(Scope):
        'A book'
        initial = 'draft'

        class Events:
            all_approved = ['draft__published']
            cancel = ['*__canceled']

        class Triggers:
            @trigger('all_approved', ['chapter:approved'])
            def publish_book(self):
                'Publishes book if all chapters are approved'
                for chapter in self.get_chapter():
                    if chapter.state != 'approved':
                        return False
                return True

    class BookEngine(Engine):
        scopes = [Book, Chapter]


Using the engine:

.. code:: python

    >>> sample = doc.instantiate({
    >>>     'body': 'Sample document',
    >>> })
    >>> sample.state
    draft

    >>> flow = sample.event('propose')
    >>> sample.state
    draft
    >>> flow.events
    [('propose', None, 'doc:draft', 'doc:proposed'), ('reject', 'check_complete', 'doc:proposed', 'doc:draft')]

    >>> sample.obj['complete'] = True
    >>> flow = sample.event('propose')
    >>> sample.state
    proposed
    >>> flow.events
    [('propose', None, 'doc:draft', 'doc:proposed')]

    >>> flow = sample.event('approve')
    Exception: Transition doc:proposed->approved failing on condition check_marked
    >>> sample.state
    proposed

    >>> sample.obj['marked'] = True
    >>> flow = sample.event('approve')
    Exception: Transition doc:proposed->approved failing on condition check_marked
    >>> sample.state
    approved
    >>> flow.events
    [('approve', None, 'doc:proposed', 'doc:approved')]


Defining the State-machine network
==================================

For a workflow state-graph we have:

:Scopes:
    The scope-of or model where the state-system lives
:States:
    The states of the scope
:Transitions:
    The transitions between scopes, with optional transition conditions.
:Events:
    Named causes of sets of transitions
:Trigger:
    Optional conditional triggers that initiates events at states


Coupling state-machines to your models
======================================

------------------------
Generating documentation
------------------------

Note: You need to have `GraphViz <http://www.graphviz.org>`_ installed.

