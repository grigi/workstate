'''WorkState engine'''
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, TypeVar

ConditionFunc = Callable[[Any], bool]
ConditionType = TypeVar('ConditionType', bound=ConditionFunc)  # pylint: disable=C0103


@dataclass
class State:
    '''A State'''
    scope: str
    state: str
    source_edges: List[str]
    dest_edges: List[str]
    triggers: List[str]
    doc: str | None


@dataclass
class Transition:
    '''A Transition'''
    scope: str
    from_state: str
    to_state: str
    condition: ConditionFunc | None
    doc: str | None

    @property
    def edge(self) -> str:
        '''Transition edge identifier'''
        return f'{self.scope}:{self.from_state}__{self.to_state}'


@dataclass
class Event:
    '''An Event'''
    event: str
    transitions: List[str]
    triggers: List[str]
    doc: str | None


@dataclass
class Trigger:
    '''A Trigger'''
    name: str
    event: str
    states: List[str]
    condition: ConditionFunc | None
    doc: str | None


@dataclass
class _Parsed:
    '''Internal Parsed representation'''
    scopes: Dict[str, str | None]
    states: States
    transitions: Transitions
    events: Events
    triggers: Triggers


class States:
    '''State container'''

    def __init__(self, scope: str | None) -> None:
        self.scope = scope
        self.states: Dict[str, State] = {}

    def fullname(self, name: str, scope: str | None = None) -> str:
        '''Returns canonical name'''
        if ':' in name:
            return name
        return f'{self.scope or scope}:{name}'

    def ensure_state(self, name: str, doc: str | None = None) -> State:
        '''Ensures that a state exists'''
        fqsn = self.fullname(name)

        if fqsn not in self.states:
            (scope, state) = fqsn.split(':')
            self.states[fqsn] = State(scope, state, [], [], [], doc)

        return self.states[fqsn]

    def merge_state(self, obj: State) -> None:
        '''Merge an external state into this one'''
        self.ensure_state(f'{obj.scope}:{obj.state}', obj.doc)

    def get_state(self, name: str, scope: str | None = None) -> State:
        '''Return state object'''
        return self.states[self.fullname(name, scope)]

    def __repr__(self) -> str:
        return repr(self.states)


class Transitions:
    '''Transition container'''

    def __init__(self, scope: str | None, states: States) -> None:
        self.scope = scope
        self.states = states
        self.transitions: Dict[str, Transition] = {}

    def fullname(self, name: str) -> str:
        '''Return canonical name'''
        if ':' in name:
            return name
        (from_state, to_state) = name.split('__')
        if not from_state or from_state == '_Transitions':
            from_state = '*'
        return f'{self.scope}:{from_state}__{to_state}'

    def ensure_transition(self,
                          name: str,
                          condition: ConditionType | None = None,
                          doc: str | None = None) -> str:
        '''Ensures that a transition exists'''
        fqsn = self.fullname(name)

        if fqsn not in self.transitions:
            (scope, edge) = fqsn.split(':')
            (from_state, to_state) = edge.split('__')
            if from_state != '*':
                fstate = self.states.ensure_state(f'{scope}:{from_state}')
                fstate.dest_edges.append(fqsn)
            tstate = self.states.ensure_state(f'{scope}:{to_state}')
            tstate.source_edges.append(fqsn)
            self.transitions[fqsn] = Transition(scope, from_state, to_state, condition, doc)

        return fqsn

    def merge_transition(self, obj: Transition) -> None:
        '''Marge an external transition into this one'''
        self.ensure_transition(obj.edge, obj.condition, obj.doc)

    def __repr__(self) -> str:
        return repr(self.transitions)


class Events:
    '''Event container'''

    def __init__(self, transs: Transitions) -> None:
        self.transs = transs
        self.events: Dict[str, Event] = {}

    def update_event(self, name: str, transitions: List[str], doc: str | None = None) -> Event:
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

    def merge_event(self, obj: Event) -> None:
        '''Merge an external event into this one'''
        self.update_event(obj.event, obj.transitions, obj.doc)

    def __repr__(self) -> str:
        return repr(self.events)


class Triggers:
    '''Trigger container'''

    def __init__(self, events: Events, states: States) -> None:
        self.events = events
        self.states = states
        self.triggers: Dict[str, Trigger] = {}

    def add_trigger(self,
                    name: str,
                    event: str,
                    states: List[str],
                    condition: ConditionType | None,
                    doc: str | None = None) -> None:
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

    def merge_trigger(self, obj: Trigger) -> None:
        '''Merge a Trigger into this one'''
        self.add_trigger(obj.name, obj.event, obj.states, obj.condition, obj.doc)

    def __repr__(self) -> str:
        return repr(self.triggers)
