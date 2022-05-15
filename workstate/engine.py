'''WorkState engine'''
from collections import namedtuple

from workstate.docgen import Digraph, BGCOLORS, FGCOLORS

__all__ = ['Engine', 'Scope', 'BrokenStateModelException', 'trigger']

class BrokenStateModelException(Exception):
    pass

State = namedtuple('State', 'scope state source_edges dest_edges triggers doc')
Transition = namedtuple('Transition', 'scope from_state to_state condition doc')
Event = namedtuple('Event', 'event transitions triggers doc')
Trigger = namedtuple('Trigger', 'name event states condition doc')

class States:
    '''State container'''
    def __init__(self, scope):
        self.scope = scope
        self.states = {}

    def fullname(self, name, scope=None):
        '''Returns canonical name'''
        if ':' in name:
            return name
        else:
            _scope = self.scope
            if _scope:
                return self.scope+':'+name
            else:
                return scope+':'+name

    def ensure_state(self, name, doc=None):
        '''Ensures that a state exists'''
        fqsn = self.fullname(name)

        if fqsn not in self.states.keys():
            (scope, state) = fqsn.split(':')
            self.states[fqsn] = State(scope, state, [], [], [], doc)

        return self.states[fqsn]

    def merge_state(self, obj):
        self.ensure_state(obj.scope+':'+obj.state, obj.doc)

    def get_state(self, name, scope=None):
        '''Return state object'''
        return self.states[self.fullname(name, scope)]

    def __repr__(self):
        return repr(self.states)


class Transitions:
    '''Transition container'''
    def __init__(self, scope, states):
        self.scope = scope
        self.states = states
        self.transitions = {}

    def fullname(self, name):
        '''Returne canonical name'''
        if ':' in name:
            return name
        else:
            (from_state, to_state) = name.split('__')
            if not from_state or from_state == '_Transitions':
                from_state = '*'
            return self.scope+':'+from_state+'__'+to_state

    def ensure_transition(self, name, condition=None, doc=None):
        '''Ensures that a transition exists'''
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

    def merge_transition(self, obj):
        self.ensure_transition(obj.scope+':'+obj.from_state+'__'+obj.to_state, obj.condition, obj.doc)

    def __repr__(self):
        return repr(self.transitions)


class Events:
    '''Event container'''
    def __init__(self, transs):
        self.transs = transs
        self.events = {}

    def update_event(self, name, transitions, doc=None):
        '''Create/Update event with provided transitions'''
        _transitions = []
        for tran in transitions:
            _transitions.append(self.transs.ensure_transition(tran))
        if name in self.events:
            event = self.events[name]
            event.transitions.extend(_transitions)
        else:
            event = self.events[name] = Event(name, _transitions, [], doc)

        return event

    def merge_event(self, obj):
        self.update_event(obj.event, obj.transitions, obj.doc)

    def __repr__(self):
        return repr(self.events)


class Triggers:
    '''Trigger container'''
    def __init__(self, events, states):
        self.events = events
        self.states = states
        self.triggers = {}

    def add_trigger(self, name, event, states, condition, doc=None):
        '''Add a trigger condition'''
        name = self.states.fullname(name)
        scope = name.split(':')[0]
        _trigger = Trigger(name, event, states, condition, doc)
        self.triggers[name] = _trigger
        self.events.update_event(event, [])
        _event = self.events.events[event]
        _event.triggers.append(name)

        for state in states:
            try:
                _state = self.states.get_state(state, scope)
                _state.triggers.append(name)
            except KeyError:
                pass

    def merge_trigger(self, obj):
        self.add_trigger(obj.name, obj.event, obj.states, obj.condition, obj.doc)

    def __repr__(self):
        return repr(self.triggers)


class ScopeMeta(type):
    '''Meta-Class for Scope'''
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
                            raise BrokenStateModelException('Events need to be one of: [], ("",[]), ([],"")')
                        events.update_event(key, edges, doc)

            if 'Triggers' in dct:
                dct_trigrs = dct['Triggers']
                tri_funs = [key for key in dir(dct_trigrs) if not key.startswith('__')]
                for _tf in tri_funs:
                    tri_fun = getattr(dct_trigrs, _tf)
                    triggers.add_trigger(tri_fun.__name__, tri_fun.event, tri_fun.states, tri_fun, tri_fun.__doc__)


        # we need to call type.__new__ to complete the initialization
        return type.__new__(mcs, name, parents, dct)


class Scope(metaclass=ScopeMeta):
    '''WorkState Scope'''
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
        _events = cls.get_parsed()['events'].events
        events = cls.get_event_map()

        # Check that each edge has an event that can trigger it
        for key, transition in _transitions.transitions.items():
            edge = transition.scope+':'+transition.from_state+'__'+transition.to_state
            if not events.get(edge, None):
                raise BrokenStateModelException("Transition %s has no events that can trigger it" % key)

        # Check that all events contains edges
        for key, val in _events.items():
            if not val.transitions:
                raise BrokenStateModelException("Event %s contains no transitions" % key)

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
                raise BrokenStateModelException("States %s not reachable from initial state" % list(pool))

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
    def graph_scope(cls, dot=None, col=0):
        '''Generates dot graph for provided scope'''
        if not dot:
            dot = Digraph()
        wildcards = set()
        initial = cls.get_initial()
        transitions = cls.get_parsed()['transs'].transitions
        events = cls.get_event_map()
        triggers = dict([(a.event, (b, a.states)) for b, a in cls.get_parsed()['trigrs'].triggers.items()])

        def canon(val, scope=None):
            '''Returns canonical edge name'''
            if ':' in val:
                return val
            if scope:
                return scope+':'+val
            else:
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
                        _trigger = triggers.get(event, None)
                        pevent = event.replace('_', ' ').title()
                        style = "dashed" if edge.condition else "solid"
                        if _trigger:
                            tname = _trigger[0].split(':')[1]
                            pretty = pevent+' <SUP><FONT POINT-SIZE="10">('+tname+')</FONT></SUP>'
                            dot.edge(canon(edge.from_state, edge.scope), canon(edge.to_state, edge.scope), pretty, style=style, color=FGCOLORS[col])
                        else:
                            dot.edge(canon(edge.from_state, edge.scope), canon(edge.to_state, edge.scope), pevent, style=style, color=FGCOLORS[col])
                else:
                    dot.edge(canon(edge.from_state, edge.scope), canon(edge.to_state, edge.scope), style="dotted", color=FGCOLORS[col])
            else:
                wildcards.add((edge.to_state, edge.scope))

        if wildcards:
            for scope in set([_wc[1] for _wc in wildcards]):
                dot.node(canon('*', scope), 'Any', shape='none', style="filled", fillcolor=BGCOLORS[col], color=FGCOLORS[col])
            for dest, scope in wildcards:
                for event in events['%s:*__%s' % (cls.get_scope(), dest)]:
                    pevent = event.replace('_', ' ').title()
                    dot.edge(canon('*', scope), canon(dest, scope), pevent, color=FGCOLORS[col])

        return dot

    @classmethod
    def graph_triggers(cls, dot, col=0):
        '''Generates dot graph for non-edge triggers'''
        transitions = cls.get_parsed()['transs'].transitions
        events = cls.get_event_map()
        triggers = dict([(a.event, (b, a.states)) for b, a in cls.get_parsed()['trigrs'].triggers.items()])

        def canon(val):
            '''Returns canonical edge name'''
            if ':' in val:
                return val
            return cls.get_scope()+':'+val


        for name, edge in transitions.items():
            if edge.from_state != '*':
                for event in events[name]:
                    _trigger = triggers.get(event, None)
                    if _trigger:
                        tname = _trigger[0].split(':')[1]
                        for trig in _trigger[1]:
                            if trig != edge.from_state:
                                dot.edge(canon(trig), canon(edge.to_state), '<FONT POINT-SIZE="10">'+tname+'</FONT>', style="dotted", color=FGCOLORS[col])

        return dot


    @classmethod
    def graph(cls, dot=None, col=0, trigger_edges=False):
        '''Generates dot graph for provided scope'''
        dot = cls.graph_scope(dot, col)
        if trigger_edges:
            cls.graph_triggers(dot, col)

        return dot

class EngineMeta(type):
    '''Meta-Class for Engine'''
    def __new__(mcs, name, parents, dct):
        if '__the_base_class__' not in dct:
            if 'scopes' not in dct or not isinstance(dct['scopes'], list):
                raise BrokenStateModelException("Engine needs scopes defined as a scope list")
            for scope in dct['scopes']:
                if '__parsed' not in dir(scope):
                    raise BrokenStateModelException("Engine needs scopes defined as a scope list")

            _scopes = dct['scopes']
            scopes = {}
            states = States(None)
            transs = Transitions(None, states)
            events = Events(transs)
            triggers = Triggers(events, states)

            dct['__parsed'] = {
                'scopes': scopes,
                'states': states,
                'transs': transs,
                'events': events,
                'trigrs': triggers
            }

            for scope in _scopes:
                spar = scope.get_parsed()

                for state in spar['states'].states.values():
                    states.merge_state(state)

                for trans in spar['transs'].transitions.values():
                    transs.merge_transition(trans)

                for event in spar['events'].events.values():
                    events.merge_event(event)

                for trigger in spar['trigrs'].triggers.values():
                    triggers.merge_trigger(trigger)

            scopenames = set([a.scope for a in states.states.values()])
            for name in scopenames:
                try:
                    scopes[name] = [a.get_initial() for a in _scopes if a.get_scope() == name][0]
                except IndexError:
                    scopes[name] = None


        # we need to call type.__new__ to complete the initialization
        cls =  type.__new__(mcs, name, parents, dct)
        if '__the_base_class__' not in dct:
            # Validate the Engine to ensure it is sane
            cls.validate()
        return cls


class Engine(metaclass=EngineMeta):
    '''WorkState Engine'''
    __the_base_class__ = True

    @classmethod
    def get_parsed(cls):
        '''returns the parsed translation lookup'''
        return getattr(cls, '__parsed')

    @classmethod
    def get_scopes(cls):
        '''Returns the current scope'''
        return getattr(cls, 'scopes')

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
    def graph(cls):
        '''Generates dot graph for whole engine'''
        # TODO: build graph from merged __parsed
        dot = Digraph()

        for idx, scope in enumerate(cls.get_scopes()):
            dot.body.append('subgraph cluster_%s {' % idx)
            dot.body.append('label="%s"' % scope.get_scope().title())
            dot.body.append('color="%s"' % FGCOLORS[idx+1])
            scope.graph_scope(dot, col=idx+1)
            dot.body.append('}')
        for idx, scope in enumerate(cls.get_scopes()):
            scope.graph_triggers(dot, col=idx+1)

        return dot

    @classmethod
    def validate(cls):
        '''Validates the WorkState Engine'''
        '''# TODO: validate against own merged __parsed
        # Validate nodes, edges and states
        for scope in cls.get_scopes():
            scope.validate()

        # TODO: Validate triggers'''

        _scopes = cls.get_parsed()['scopes']
        _states = cls.get_parsed()['states'].states
        _transitions = cls.get_parsed()['transs']
        _events = cls.get_parsed()['events'].events
        events = cls.get_event_map()

        # Check that each edge has an event that can trigger it
        for key, transition in _transitions.transitions.items():
            edge = transition.scope+':'+transition.from_state+'__'+transition.to_state
            if not events.get(edge, None):
                raise BrokenStateModelException("Transition %s has no events that can trigger it" % key)

        # Check that all events contains edges
        for key, val in _events.items():
            if not val.transitions:
                raise BrokenStateModelException("Event %s contains no transitions" % key)

        # Check that all states are connected
        for scope, initial in _scopes.items():
            if initial:
                pool = set([a for a,b in _states.items() if b.scope == scope])
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
                    raise BrokenStateModelException("States %s not reachable from initial state in scope %s" % (list(pool), scope))


def trigger(event, states):
    '''Annotates the condition function with event and states attributes'''
    def _wrap(fun):
        # pylint: disable=C0111
        fun.event = event
        fun.states = states
        return fun
    return _wrap

