'''WorkState engine'''
from collections import namedtuple
try:
    from collections import OrderedDict #pylint: disable=F0401
except ImportError:
    from ordereddict import OrderedDict #pylint: disable=F0401

State = namedtuple('State', 'scope state source_edges dest_edges events doc')
Transition = namedtuple('Transition', 'scope from_state to_state condition transitions doc')
Event = namedtuple('Event', 'event transitions condition doc')

class Engine(object):
    '''Workstate Engine'''

    def __init__(self):

        self.scopes = OrderedDict()
        self.states = {}
        self.transitions = {}
        self.events = {}

    def dict(self):
        '''Returns engine spec as dict'''
        return dict(scopes=self.scopes, states=self.states, transs=self.transitions, events=self.events)

    def add_event(self, event, transitions, condition=None, doc=None):
        '''Registers an event that fires on a condition of a set of states'''
        if event in self.events.keys():
            raise Exception("Event %s already defined" % event)
        _event = Event(event, transitions, condition, doc)
        for transition in transitions:
            _transition = self.transitions.get(transition, None)
            if not _transition:
                raise Exception("Transition %s doesn't exist" % transition)
            for state in set([val.split('->')[0] for val in _transition.transitions]):
                self.states[state].events.append(_event)

        self.events[event] = _event

    def validate(self):
        '''Validates entire WorkState Engine'''
        for scope in self.scopes.values():
            scope.validate()

class Scope(object):
    '''WorkState Scope'''

    def __init__(self, engine, scope, initial=None, states=None, doc=None):
        self.engine = engine
        self.scope = scope
        self.states = {}
        self.initial = initial
        self.transitions = {}
        self.doc = doc
        if states:
            for state, sdoc in states.items():
                self.ensure_state(state, sdoc)
        if initial:
            self.ensure_state(initial)
        self.engine.scopes[self.scope] = self

    def get_event_map(self):
        '''Returns event to transitions map'''
        transs = [trans for val in self.engine.events.values() for trans in val.transitions]
        events = [(trans, [val.event.replace('_', ' ').title() for val in self.engine.events.values() if trans in val.transitions]) for trans in transs]
        # Bah! py26 doesn't support dict evaluations!
        ret = {}
        for key, val in events:
            ret[key] = val
        return ret

    def order_states(self):
        '''Returns a list of states ordered from initial node to termination nodes'''
        if not self.initial:
            return self.states.keys()
        pool = set(self.states.keys())
        order = []

        def mark_states(statename):
            '''Recursivley mark states that are accesible'''
            if statename in pool:
                pool.remove(statename)
                order.append(statename)
            state = self.states[statename]
            for substate in set(state.dest_edges).intersection(pool):
                mark_states(substate)
        mark_states(self.initial)

        return order

    def validate(self):
        '''Validates the WorkState Scope'''

        # Check that each edge has an event that can trigger it
        events = self.get_event_map()
        for edge in self.transitions.values():
            transition = edge.transitions[0]
            if edge.from_state == '*':
                transition = '%s:*->%s' % (self.scope, edge.to_state)
            if not events.get(transition, None):
                raise Exception("Transition %s has no events that can trigger it" % transition)

        # Check that all states are connected
        if self.initial:
            pool = set(self.states.keys())
            order = []

            def mark_states(statename):
                '''Recursivley mark states that are accesible'''
                if statename in pool:
                    pool.remove(statename)
                    order.append(statename)
                state = self.states[statename]
                for substate in set(state.dest_edges).intersection(pool):
                    mark_states(substate)
            mark_states(self.initial)

            if pool:
                raise Exception("States %s not reachable from initial state" % list(pool))

    def __repr__(self):
        return "Scope(scope=%s, initial=%s, states=%s, transitions=%s doc=%s)" % (
            repr(self.scope),
            repr(self.initial),
            repr(self.states.keys()),
            repr(self.transitions.keys()),
            repr(self.doc)
        )

    def ensure_state(self, state, doc=None):
        '''Registers a state in the Scope'''
        if state not in self.states:
            _state = State(self.scope, state, [], [], [], doc)
            self.states[state] = _state
            self.engine.states['%s:%s' % (self.scope, state)] = _state

    def add_transition(self, from_state, to_state, condition=None, doc=None, transition=None):
        '''Registers a transition in the Scope'''
        if from_state == '*':
            transition = Transition(self.scope, from_state, to_state, condition, [], doc)
            for state in list(self.states):
                if state != to_state:
                    self.add_transition(state, to_state, condition, doc, transition)
            transname = '%s:%s->%s' % (self.scope, from_state, to_state)
            self.engine.transitions[transname] = transition
            return

        if type(from_state) is list:
            for state in from_state:
                self.add_transition(state, to_state, condition, doc)
            return

        self.ensure_state(from_state)
        self.ensure_state(to_state)

        edge = '%s->%s' % (from_state, to_state)
        transname = '%s:%s' % (self.scope, edge)
        if self.transitions.get(edge, None):
            raise Exception("Transition %s already defined" % transname)

        if transition:
            transition.transitions.append(transname)
            _transition = Transition(self.scope, '*', to_state, condition, [transname], doc)
        else:
            _transition = Transition(self.scope, from_state, to_state, condition, [transname], doc)
        self.transitions[edge] = _transition
        self.engine.transitions[transname] = _transition
        self.states[from_state].dest_edges.append(to_state)
        self.states[to_state].source_edges.append(from_state)
