=========
WorkState
=========

WorkState is a self-documenting Workflow-event state management system.

.. image:: https://travis-ci.org/grigi/workstate.png
   :target: https://travis-ci.org/grigi/workstate

-----
Usage
-----

Specifying workstate engine:

.. code:: python

    from workstate import Engine

    engine = Engine()
    doc = engine.scope('doc', initial='draft')

    def check_marked(obj):
        return obj.get('marked', False)

    doc.add_transition('proposed', 'approved', condition=check_marked)
    doc.add_transition('draft', 'proposed')
    doc.add_transition('proposed', 'draft')

    engine.add_event('propose', ['doc:draft->proposed'])
    engine.add_event('approve', ['doc:proposed->approved'])
    engine.add_event('reject', ['doc:proposed->draft'])

    def check_complete(obj):
        return obj.get('complete', False)

    engine.add_trigger('reject', ['doc:proposed'], condition=check_complete)

    def get_doc_state(obj):
        return obj.get('state', doc.initial)

    def set_doc_state(obj, state):
        obj['state'] = state

    doc.set_state_property(get_doc_state, set_doc_state)

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

