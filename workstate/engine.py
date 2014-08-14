'''WorkState engine'''
from __future__ import print_function

from collections import namedtuple

from six import add_metaclass

from workstate.docgen import Digraph, BGCOLORS, FGCOLORS

__all__ = ['Engine', 'Scope', 'trigger']


State = namedtuple('State', 'scope state source_edges dest_edges triggers doc')
Transition = namedtuple('Transition', 'scope from_state to_state condition doc')
Event = namedtuple('Event', 'event transitions triggers doc')
Trigger = namedtuple('Trigger', 'event states condition doc')

class States(object):
    def __init__(self, scope):
        self.scope = scope
        self.states = {}

    def fullname(self, name):
        return name if ':' in name else self.scope+':'+name

    def ensure_state(self, name, doc=None):
        fqsn = self.fullname(name)

        if fqsn not in self.states.keys():
            (scope, state) = fqsn.split(':')
            self.states[fqsn] = State(scope, state, [], [], [], doc)

        return self.states[fqsn]

    def get_state(self, name):
        return self.states[self.fullname(name)]

    def __repr__(self):
        return repr(self.states)


class Transitions(object):
    def __init__(self, scope, states):
        self.scope = scope
        self.states = states
        self.transitions = {}

    def fullname(self, name):
        if ':' in name:
            return name
        else:
            (from_state, to_state) = name.split('__')
            if not from_state or from_state == '_Transitions':
                from_state = '*'
            return self.scope+':'+from_state+'__'+to_state

    def ensure_transition(self, name, condition=None, doc=None):
        fqsn = self.fullname(name)

        if fqsn not in self.transitions.keys():
            (scope, edge) = fqsn.split(':')
            (from_state, to_state) = edge.split('__')
            if from_state != '*':
                fstate = self.states.ensure_state(scope+':'+from_state)
                fstate.dest_edges.append(fqsn)
            tstate = self.states.ensure_state(scope+':'+to_state)
            tstate.source_edges.append(fqsn)
            self.transitions[fqsn] = Transition(scope, from_state, to_state, condition, doc)

        return fqsn

    def __repr__(self):
        return repr(self.transitions)


class Events(object):
    def __init__(self, transs):
        self.transs = transs
        self.events = {}

    def update_event(self, name, transitions, doc=None):
        _transitions = []
        for tran in transitions:
            _transitions.append(self.transs.ensure_transition(tran))
        if name in self.events:
            event = self.events[name]
            event.transitions.extend(_transitions)
        else:
            event = self.events[name] = Event(name, _transitions, [], doc)

        return event

    def __repr__(self):
        return repr(self.events)


class Triggers(object):
    def __init__(self, events, states):
        self.events = events
        self.states = states
        self.triggers = {}

    def add_trigger(self, name, event, states, condition, doc=None):
        name = self.states.fullname(name)
        _trigger = Trigger(event, states, condition, doc)
        self.triggers[name] = _trigger
        _event = self.events.events[event]
        _event.triggers.append(name)

        for state in states:
            try:
                _state = self.states.get_state(state)
                _state.triggers.append(name)
            except KeyError:
                pass

    def __repr__(self):
        return repr(self.triggers)


class ScopeMeta(type):
    def __new__(mcs, name, parents, dct):

        if '__the_base_class__' not in dct:
            # create a class_id if it's not specified
            if 'scope' not in dct:
                dct['scope'] = name.lower()
            scope = dct['scope']

            states = States(scope)
            transs = Transitions(scope, states)
            events = Events(transs)
            triggers = Triggers(events, states)

            dct['__parsed'] = {
                'scope': dct['scope'],
                'states': states,
                'transs': transs,
                'events': events,
                'trigrs': triggers
            }

            if 'States' in dct:
                dct_states = dct['States']
                statekeys = [key for key in dir(dct_states) if not key.startswith('__')]
                for key in statekeys:
                    states.ensure_state(key, doc=getattr(dct_states, key))

            if 'initial' in dct:
                states.ensure_state(scope+':'+dct['initial'])

            if 'Transitions' in dct:
                dct_transs = dct['Transitions']
                transkeys = [key for key in dir(dct_transs) if not key.startswith('__')]
                for key in transkeys:
                    item = getattr(dct_transs, key)
                    #mkey = key.
                    if callable(item):
                        transs.ensure_transition(key, condition=item, doc=item.__doc__)
                    else:
                        transs.ensure_transition(key, doc=item)

            if 'Events' in dct:
                dct_events = dct['Events']
                eventkeys = [key for key in dir(dct_events) if not key.startswith('__')]
                for key in eventkeys:
                    val = getattr(dct_events, key)
                    if isinstance(val, list):
                        events.update_event(key, val)
                    elif isinstance(val, tuple):
                        try:
                            if len(val) != 2:
                                raise IndexError
                            edges = [a for a in val if isinstance(a, list)][0]
                            doc = [a for a in val if isinstance(a, str)][0]
                        except IndexError:
                            raise Exception('Events need to be one of: [], ("",[]), ([],"")')
                        events.update_event(key, edges, doc)

            if 'Triggers' in dct:
                dct_trigrs = dct['Triggers']
                tri_funs = [key for key in dir(dct_trigrs) if not key.startswith('__')]
                for _tf in tri_funs:
                    tri_fun = getattr(dct_trigrs, _tf)
                    triggers.add_trigger(tri_fun.__name__, tri_fun.event, tri_fun.states, tri_fun, tri_fun.__doc__)


        # we need to call type.__new__ to complete the initialization
        return type.__new__(mcs, name, parents, dct)


@add_metaclass(ScopeMeta)
class Scope(object):
    __the_base_class__ = True

    @classmethod
    def get_parsed(cls):
        '''returns the parsed translation lookup'''
        return getattr(cls, '__parsed')

    @classmethod
    def get_initial(cls):
        '''Returns the initial state'''
        return getattr(cls, 'initial', None)

    @classmethod
    def get_scope(cls):
        '''Returns the current scope'''
        return getattr(cls, 'scope')

    @classmethod
    def get_event_map(cls):
        '''Maps edges to transitions'''
        _events = cls.get_parsed()['events'].events
        _transitions = cls.get_parsed()['transs']

        events = {}
        for event in _events.values():
            for _trans in event.transitions:
                trans = _transitions.fullname(_trans)
                events.setdefault(trans, [])
                events[trans].append(event.event)

        return events

    @classmethod
    def validate(cls):
        '''Validates the Scope'''
        scope = cls.get_scope()
        _states = cls.get_parsed()['states'].states
        _transitions = cls.get_parsed()['transs']
        events = cls.get_event_map()

        # Check that each edge has an event that can trigger it
        for key, transition in _transitions.transitions.items():
            edge = transition.scope+':'+transition.from_state+'__'+transition.to_state
            if not events.get(edge, None):
                raise Exception("Transition %s has no events that can trigger it" % key)

        # Check that all states are connected
        initial = cls.get_initial()
        if initial:
            pool = set(_states.keys())
            order = []

            def mark_states(statename):
                '''Recursivley mark states that are accesible'''
                if statename in pool:
                    pool.remove(statename)
                    order.append(statename)
                state = _states[statename]
                dest_edges = [_transitions.transitions[edge] for edge in state.dest_edges]
                dest_states = [a.scope+':'+a.to_state for a in dest_edges]
                for substate in set(dest_states).intersection(pool):
                    mark_states(substate)
            mark_states(scope+':'+initial)

            # Wildcard states
            for event in events.keys():
                (from_state, to_state) = event.split('__')
                if '*' in from_state:
                    for _state in list(pool):
                        (scope, state) = _state.split(':')
                        if state == to_state:
                            pool.remove(_state)
                            order.append(_state)

            if pool:
                raise Exception("States %s not reachable from initial state" % list(pool))

    @classmethod
    def order_states(cls):
        '''Orders states from initial to end-states if initial is set'''
        states = cls.get_parsed()['states'].states
        initial = cls.get_initial()
        if initial:
            pool = set(states.keys())
            order = []
            transitions = cls.get_parsed()['transs'].transitions
            scope = cls.get_scope()
            events = cls.get_event_map()

            def mark_states(statename):
                '''Recursivley mark states that are accesible'''
                if statename in pool:
                    pool.remove(statename)
                    order.append(statename)
                state = states[statename]
                dest_edges = [transitions[edge] for edge in state.dest_edges]
                dest_states = [a.scope+':'+a.to_state for a in dest_edges]
                for substate in set(dest_states).intersection(pool):
                    mark_states(substate)
            mark_states(scope+':'+initial)

            # Wildcard states go last
            for event in events.keys():
                (from_state, to_state) = event.split('__')
                if '*' in from_state:
                    for _state in list(pool):
                        (scope, state) = _state.split(':')
                        if state == to_state:
                            pool.remove(_state)
                            order.append(_state)

            return order
        else:
            return states.keys()

    @classmethod
    def _graph_scope(cls, dot=None, col=0):
        '''Generates dot graph for provided scope'''

        if not dot:
            dot = Digraph()
        wildcards = set()
        initial = cls.get_initial()
        transitions = cls.get_parsed()['transs'].transitions
        events = cls.get_event_map()
        triggers = dict([(a.event, (b,a.states)) for b,a in cls.get_parsed()['trigrs'].triggers.items()])

        def canon(val):
            '''Returns canonical edge name'''
            if ':' in val:
                return val
            return cls.get_scope()+':'+val

        for fullstate in cls.order_states():
            state = fullstate.split(':')[1]
            pretty = state.replace('_', ' ').title()
            if state == initial:
                dot.node(fullstate, pretty, shape='oval', rank="max", style="bold,filled", fillcolor=BGCOLORS[col], color=FGCOLORS[col])
            else:
                dot.node(fullstate, pretty, shape='rectangle', style="filled,rounded", fillcolor=BGCOLORS[col], color=FGCOLORS[col])

        for name, edge in transitions.items():
            if edge.from_state != '*':
                if name in events:
                    for event in events[name]:
                        trigger = triggers.get(event, None)
                        pevent = event.replace('_', ' ').title()
                        style = "dashed" if edge.condition else "solid"
                        if trigger:
                            tname = trigger[0].split(':')[1]
                            dot.edge(canon(edge.from_state), canon(edge.to_state), pevent+' <SUP><FONT POINT-SIZE="10">('+tname+')</FONT></SUP>', style=style, color=FGCOLORS[col])
                        else:
                            dot.edge(canon(edge.from_state), canon(edge.to_state), pevent, style=style, color=FGCOLORS[col])
                else:
                    dot.edge(canon(edge.from_state), canon(edge.to_state), style="dotted", color=FGCOLORS[col])
            else:
                wildcards.add(edge.to_state)

        if wildcards:
            dot.node(canon('*'), 'Any', shape='none', style="filled", fillcolor=BGCOLORS[col], color=FGCOLORS[col])
            for dest in wildcards:
                for event in events['%s:*__%s' % (cls.get_scope(), dest)]:
                    pevent = event.replace('_', ' ').title()
                    dot.edge(canon('*'), canon(dest), pevent, color=FGCOLORS[col])

        return dot

    @classmethod
    def _graph_triggers(cls, dot, col=0):
        '''Generates dot graph for non-edge triggers'''

        transitions = cls.get_parsed()['transs'].transitions
        events = cls.get_event_map()
        triggers = dict([(a.event, (b,a.states)) for b,a in cls.get_parsed()['trigrs'].triggers.items()])

        def canon(val):
            '''Returns canonical edge name'''
            if ':' in val:
                return val
            return cls.get_scope()+':'+val


        for name, edge in transitions.items():
            if edge.from_state != '*':
                for event in events[name]:
                    trigger = triggers.get(event, None)
                    if trigger:
                        tname = trigger[0].split(':')[1]
                        for t in trigger[1]:
                            if t!=edge.from_state:
                                dot.edge(canon(t), canon(edge.to_state), '<FONT POINT-SIZE="10">'+tname+'</FONT>', style="dotted", color=FGCOLORS[col])

        return dot


    @classmethod
    def graph(cls, dot=None, col=0, trigger_edges=False):
        '''Generates dot graph for provided scope'''

        dot = cls._graph_scope(dot, col)
        if trigger_edges:
            cls._graph_triggers(dot, col)

        return dot

class EngineMeta(type):
    def __new__(mcs, name, parents, dct):

        if '__the_base_class__' not in dct:
            if 'scopes' not in dct or not isinstance(dct['scopes'], list):
                raise Exception("Engine needs scopes defined as a scope list")
            for scope in dct['scopes']:
                if '__parsed' not in dir(scope):
                    raise Exception("Engine needs scopes defined as a scope list")

        # TODO: Merge __parsed translations lookups

        # we need to call type.__new__ zto complete the initialization
        return type.__new__(mcs, name, parents, dct)


@add_metaclass(EngineMeta)
class Engine(object):
    __the_base_class__ = True

    @classmethod
    def graph(cls):
        '''Generates dot graph for whole engine'''

        dot = Digraph()

        for idx, scope in enumerate(cls.scopes):
            dot.body.append('subgraph cluster_%s {' % idx)
            dot.body.append('label="%s"' % scope.get_scope().title())
            dot.body.append('color="%s"' % FGCOLORS[idx+1])
            scope._graph_scope(dot, col=idx+1)
            dot.body.append('}')
        for idx, scope in enumerate(cls.scopes):
            scope._graph_triggers(dot, col=idx+1)

        return dot

    @classmethod
    def validate(cls):
        # Validate nodes, edges and states
        for scope in cls.scopes:
            scope.validate()

        # TODO: Validate triggers


def trigger(event, states):
    'Annotates the condition function with event and states attributes'
    def _wrap(f):
        f.event = event
        f.states = states
        return f
    return _wrap
