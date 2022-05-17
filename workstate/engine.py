'''WorkState engine'''
from __future__ import annotations

from typing import Callable, Dict, List, Set

from workstate.docgen import BGCOLORS, FGCOLORS, Digraph
from workstate.engine_graph import (ConditionType, Events, State, States, Transitions, Triggers,
                                    _Parsed)
from workstate.exceptions import BrokenStateModelException

__all__ = ['Engine', 'Scope', 'BrokenStateModelException', 'trigger']


class ScopeMeta(type):
    '''Meta-Class for Scope'''

    def __new__(mcs, name: str, parents: tuple, dct: dict) -> type:
        if '__the_base_class__' not in dct:
            # create a class_id if it's not specified
            if 'scope' not in dct:
                dct['scope'] = name.lower()
            scope = dct['scope']

            states = States(scope)
            transs = Transitions(scope, states)
            events = Events(transs)
            triggers = Triggers(events, states)

            dct['__parsed'] = _Parsed(dct['scope'], states, transs, events, triggers)

            if 'States' in dct:
                dct_states = dct['States']
                statekeys = [key for key in dir(dct_states) if not key.startswith('__')]
                for key in statekeys:
                    states.ensure_state(key, doc=getattr(dct_states, key))

            if 'initial' in dct:
                states.ensure_state(f"{scope}:{dct['initial']}")

            if 'Transitions' in dct:
                dct_transs = dct['Transitions']
                transkeys = [key for key in dir(dct_transs) if not key.startswith('__')]
                for key in transkeys:
                    item = getattr(dct_transs, key)
                    # mkey = key.
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
                        except IndexError as exc:
                            raise BrokenStateModelException(
                                'Events need to be one of: [], ("",[]), ([],"")'
                            ) from exc
                        events.update_event(key, edges, doc)

            if 'Triggers' in dct:
                dct_trigrs = dct['Triggers']
                tri_funs = [key for key in dir(dct_trigrs) if not key.startswith('__')]
                for _tf in tri_funs:
                    tri_fun = getattr(dct_trigrs, _tf)
                    triggers.add_trigger(
                        tri_fun.__name__, tri_fun.event, tri_fun.states, tri_fun, tri_fun.__doc__
                    )

        # we need to call type.__new__ to complete the initialization
        return type.__new__(mcs, name, parents, dct)


class Scope(metaclass=ScopeMeta):
    '''WorkState Scope'''

    __the_base_class__ = True

    @classmethod
    def get_parsed(cls) -> _Parsed:
        '''returns the parsed translation lookup'''
        return getattr(cls, '__parsed')  # type: ignore

    @classmethod
    def get_initial(cls) -> str | None:
        '''Returns the initial state'''
        return getattr(cls, 'initial', None)

    @classmethod
    def get_scope(cls) -> str:
        '''Returns the current scope'''
        return getattr(cls, 'scope')  # type: ignore

    @classmethod
    def get_event_map(cls) -> Dict[str, List[str]]:
        '''Maps edges to transitions'''
        _events = cls.get_parsed().events.events
        _transitions = cls.get_parsed().transitions

        events: Dict[str, List[str]] = {}
        for event in _events.values():
            for _trans in event.transitions:
                trans = _transitions.fullname(_trans)
                events.setdefault(trans, [])
                events[trans].append(event.event)

        return events

    @classmethod
    def validate(cls) -> None:
        '''Validates the Scope'''
        scope = cls.get_scope()
        _states = cls.get_parsed().states.states
        _transitions = cls.get_parsed().transitions
        _events = cls.get_parsed().events.events
        events = cls.get_event_map()

        # Check that each edge has an event that can trigger it
        for key, transition in _transitions.transitions.items():
            if not events.get(transition.edge, None):
                raise BrokenStateModelException(
                    f"Transition {key} has no events that can trigger it"
                )

        # Check that all events contains edges
        for key, val in _events.items():
            if not val.transitions:
                raise BrokenStateModelException(f"Event {key} contains no transitions")

        # Check that all states are connected
        initial = cls.get_initial()
        if initial:
            pool = set(_states.keys())
            order = []

            def mark_states(statename: str) -> None:
                '''Recursively mark states that are accessible'''
                if statename in pool:
                    pool.remove(statename)
                    order.append(statename)
                state = _states[statename]
                dest_edges = [_transitions.transitions[edge] for edge in state.dest_edges]
                dest_states = [a.scope + ':' + a.to_state for a in dest_edges]
                for substate in set(dest_states).intersection(pool):
                    mark_states(substate)

            mark_states(scope + ':' + initial)

            # Wildcard states
            for event in events:
                (from_state, to_state) = event.split('__')
                if '*' in from_state:
                    for _state in list(pool):
                        (scope, state) = _state.split(':')
                        if state == to_state:
                            pool.remove(_state)
                            order.append(_state)

            if pool:
                raise BrokenStateModelException(
                    f"States {list(pool)} not reachable from initial state"
                )

    @classmethod
    def order_states(cls) -> List[str]:
        '''Orders states from initial to end-states if initial is set'''
        states: Dict[str, State] = cls.get_parsed().states.states
        initial = cls.get_initial()

        if initial is None:
            return list(states.keys())

        pool = set(states.keys())
        order = []
        transitions = cls.get_parsed().transitions.transitions
        scope = cls.get_scope()
        events = cls.get_event_map()

        def mark_states(statename: str) -> None:
            '''Recursivley mark states that are accesible'''
            if statename in pool:
                pool.remove(statename)
                order.append(statename)
            state = states[statename]
            dest_edges = [transitions[edge] for edge in state.dest_edges]
            dest_states = [a.scope + ':' + a.to_state for a in dest_edges]
            for substate in set(dest_states).intersection(pool):
                mark_states(substate)

        mark_states(scope + ':' + initial)

        # Wildcard states go last
        for event in events:
            (from_state, to_state) = event.split('__')
            if '*' in from_state:
                for _state in list(pool):
                    (scope, state) = _state.split(':')
                    if state == to_state:
                        pool.remove(_state)
                        order.append(_state)

        return order

    @classmethod
    def graph_scope(cls, dot: Digraph | None = None, col: int = 0) -> Digraph:
        '''Generates dot graph for provided scope'''
        if not dot:
            dot = Digraph()
        wildcards = set()
        initial = cls.get_initial()
        transitions = cls.get_parsed().transitions.transitions
        events = cls.get_event_map()
        triggers = {
            a.event: (b, a.states) for b, a in cls.get_parsed().triggers.triggers.items()
        }

        def canon(val: str, scope: str | None = None) -> str:
            '''Returns canonical edge name'''
            if ':' in val:
                return val
            if scope:
                return scope + ':' + val
            return cls.get_scope() + ':' + val

        for fullstate in cls.order_states():
            state = fullstate.split(':')[1]
            pretty = state.replace('_', ' ').title()
            if state == initial:
                dot.node(
                    fullstate,
                    pretty,
                    shape='oval',
                    rank="max",
                    style="bold,filled",
                    fillcolor=BGCOLORS[col],
                    color=FGCOLORS[col],
                )
            else:
                dot.node(
                    fullstate,
                    pretty,
                    shape='rectangle',
                    style="filled,rounded",
                    fillcolor=BGCOLORS[col],
                    color=FGCOLORS[col],
                )

        for name, edge in transitions.items():
            if edge.from_state != '*':
                if name in events:
                    for event in events[name]:
                        _trigger = triggers.get(event, None)
                        pevent = event.replace('_', ' ').title()
                        style = "dashed" if edge.condition else "solid"
                        if _trigger:
                            tname = _trigger[0].split(':')[1]
                            pretty = (
                                pevent + ' <SUP><FONT POINT-SIZE="10">(' + tname + ')</FONT></SUP>'
                            )
                            dot.edge(
                                canon(edge.from_state, edge.scope),
                                canon(edge.to_state, edge.scope),
                                pretty,
                                style=style,
                                color=FGCOLORS[col],
                            )
                        else:
                            dot.edge(
                                canon(edge.from_state, edge.scope),
                                canon(edge.to_state, edge.scope),
                                pevent,
                                style=style,
                                color=FGCOLORS[col],
                            )
                else:
                    dot.edge(
                        canon(edge.from_state, edge.scope),
                        canon(edge.to_state, edge.scope),
                        style="dotted",
                        color=FGCOLORS[col],
                    )
            else:
                wildcards.add((edge.to_state, edge.scope))

        if wildcards:
            for scope in {_wc[1] for _wc in wildcards}:
                dot.node(
                    canon('*', scope),
                    'Any',
                    shape='none',
                    style="filled",
                    fillcolor=BGCOLORS[col],
                    color=FGCOLORS[col],
                )
            for dest, scope in wildcards:
                for event in events[f'{cls.get_scope()}:*__{dest}']:
                    pevent = event.replace('_', ' ').title()
                    dot.edge(canon('*', scope), canon(dest, scope), pevent, color=FGCOLORS[col])

        return dot

    @classmethod
    def graph_triggers(cls, dot: Digraph, col: int = 0) -> Digraph:
        '''Generates dot graph for non-edge triggers'''
        transitions = cls.get_parsed().transitions.transitions
        events = cls.get_event_map()
        triggers = {
            a.event: (b, a.states) for b, a in cls.get_parsed().triggers.triggers.items()
        }

        def canon(val: str) -> str:
            '''Returns canonical edge name'''
            if ':' in val:
                return val
            return cls.get_scope() + ':' + val

        for name, edge in transitions.items():
            if edge.from_state != '*':
                for event in events[name]:
                    _trigger = triggers.get(event, None)
                    if _trigger:
                        tname = _trigger[0].split(':')[1]
                        for trig in _trigger[1]:
                            if trig != edge.from_state:
                                dot.edge(
                                    canon(trig),
                                    canon(edge.to_state),
                                    '<FONT POINT-SIZE="10">' + tname + '</FONT>',
                                    style="dotted",
                                    color=FGCOLORS[col],
                                )

        return dot

    @classmethod
    def graph(cls,
              dot: Digraph | None = None,
              col: int = 0,
              trigger_edges: bool = False) -> Digraph:
        '''Generates dot graph for provided scope'''
        dot = cls.graph_scope(dot, col)
        if trigger_edges:
            cls.graph_triggers(dot, col)

        return dot


class EngineMeta(type):
    '''Meta-Class for Engine'''

    def __new__(mcs, name: str, parents: tuple, dct: dict) -> type:
        if '__the_base_class__' not in dct:
            if 'scopes' not in dct or not isinstance(dct['scopes'], list):
                raise BrokenStateModelException("Engine needs scopes defined as a scope list")
            for scope in dct['scopes']:
                if '__parsed' not in dir(scope):
                    raise BrokenStateModelException("Engine needs scopes defined as a scope list")

            _scopes: List[Scope] = dct['scopes']
            scopes: Dict[str, str | None] = {}
            states = States(None)
            transs = Transitions(None, states)
            events = Events(transs)
            triggers = Triggers(events, states)

            dct['__parsed'] = _Parsed(scopes, states, transs, events, triggers)

            for scope in _scopes:
                spar = scope.get_parsed()

                for state in spar.states.states.values():
                    states.merge_state(state)

                for trans in spar.transitions.transitions.values():
                    transs.merge_transition(trans)

                for event in spar.events.events.values():
                    events.merge_event(event)

                for _trigger in spar.triggers.triggers.values():
                    triggers.merge_trigger(_trigger)

            scopenames = {a.scope for a in states.states.values()}
            for _name in scopenames:
                try:
                    scopes[_name] = [a.get_initial() for a in _scopes if a.get_scope() == _name][0]
                except IndexError:
                    scopes[_name] = None

        # we need to call type.__new__ to complete the initialization
        cls: Engine = type.__new__(mcs, name, parents, dct)  # type: ignore
        if '__the_base_class__' not in dct:
            # Validate the Engine to ensure it is sane
            cls.validate()
        return cls  # type: ignore


class Engine(metaclass=EngineMeta):
    '''WorkState Engine'''

    __the_base_class__ = True

    @classmethod
    def get_parsed(cls) -> _Parsed:
        '''returns the parsed translation lookup'''
        return getattr(cls, '__parsed')  # type: ignore

    @classmethod
    def get_scopes(cls) -> List[Scope]:
        '''Returns the current scope'''
        return getattr(cls, 'scopes')  # type: ignore

    @classmethod
    def get_event_map(cls) -> Dict[str, List[str]]:
        '''Maps edges to transitions'''
        _events = cls.get_parsed().events.events
        _transitions = cls.get_parsed().transitions

        events: Dict[str, List[str]] = {}
        for event in _events.values():
            for _trans in event.transitions:
                trans = _transitions.fullname(_trans)
                events.setdefault(trans, [])
                events[trans].append(event.event)

        return events

    @classmethod
    def graph(cls) -> Digraph:
        '''Generates dot graph for whole engine'''
        # TODO: build graph from merged __parsed
        dot = Digraph()

        for idx, scope in enumerate(cls.get_scopes()):
            dot.body.append(f'subgraph cluster_{idx} {{')
            dot.body.append(f'label="{scope.get_scope().title()}"')
            dot.body.append(f'color="{FGCOLORS[idx + 1]}"')
            scope.graph_scope(dot, col=idx + 1)
            dot.body.append('}')
        for idx, scope in enumerate(cls.get_scopes()):
            scope.graph_triggers(dot, col=idx + 1)

        return dot

    @classmethod
    def validate(cls) -> None:
        '''Validates the WorkState Engine'''

        # TODO: validate against own merged __parsed
        # Validate nodes, edges and states
        for _scope in cls.get_scopes():
            _scope.validate()

        # TODO: Validate triggers

        _scopes = cls.get_parsed().scopes
        _states = cls.get_parsed().states.states
        _transitions = cls.get_parsed().transitions
        _events = cls.get_parsed().events.events
        events = cls.get_event_map()

        # Check that each edge has an event that can trigger it
        for key, transition in _transitions.transitions.items():
            edge = transition.scope + ':' + transition.from_state + '__' + transition.to_state
            if not events.get(edge, None):
                raise BrokenStateModelException(
                    f"Transition {key} has no events that can trigger it"
                )

        # Check that all events contains edges
        for key, val in _events.items():
            if not val.transitions:
                raise BrokenStateModelException(f"Event {key} contains no transitions")

        def mark_states(statename: str, pool: Set[str], order: List[str]) -> None:
            '''Recursively mark states that are accessible'''
            if statename in pool:
                pool.remove(statename)
                order.append(statename)
            state = _states[statename]
            dest_edges = [_transitions.transitions[edge] for edge in state.dest_edges]
            dest_states = [a.scope + ':' + a.to_state for a in dest_edges]
            for substate in set(dest_states).intersection(pool):
                mark_states(substate, pool, order)

        # Check that all states are connected
        for scope, initial in _scopes.items():
            if initial:
                pool = {a for a, b in _states.items() if b.scope == scope}
                order: List[str] = []

                mark_states(scope + ':' + initial, pool, order)

                # Wildcard states
                for event in events:
                    (from_state, to_state) = event.split('__')
                    if '*' in from_state:
                        for _state in list(pool):
                            (scope, state) = _state.split(':')
                            if state == to_state:
                                pool.remove(_state)
                                order.append(_state)

                if pool:
                    raise BrokenStateModelException(
                        f"States {list(pool)} not reachable from initial state in scope {scope}"
                    )


def trigger(event: str, states: List[str]) -> Callable[[ConditionType], ConditionType]:
    '''Annotates the condition function with event and states attributes'''

    def _wrap(fun: ConditionType) -> ConditionType:
        fun.event = event  # type: ignore
        fun.states = states  # type: ignore
        return fun

    return _wrap
