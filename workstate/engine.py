'''WorkState engine'''
from __future__ import annotations

from typing import Callable, Dict, List

from workstate.docgen import FGCOLORS, Digraph
from workstate.engine_graph import ConditionType, Events, States, Transitions, Triggers, _Parsed
from workstate.exceptions import BrokenStateModelException
from workstate.scope import Scope
from workstate.utils import check_edges, mark_states

__all__ = ['Engine', 'Scope', 'BrokenStateModelException', 'trigger']

# pylint: disable=R0801


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

        check_edges(_transitions, events, _events)

        # Check that all states are connected
        for scope, initial in _scopes.items():
            if initial:
                pool = {a for a, b in _states.items() if b.scope == scope}
                order: List[str] = []

                mark_states(_states, _transitions, f'{scope}:{initial}', pool, order, events)

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
