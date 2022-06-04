'''WorkState engine'''
from __future__ import annotations

from typing import Dict, List, Set

from workstate.engine_graph import Event, State, Transitions
from workstate.exceptions import BrokenStateModelException


def mark_states(_states: Dict[str, State],
                _transitions: Transitions,
                statename: str,
                pool: Set[str],
                order: List[str],
                events: Dict[str, List[str]]) -> None:
    '''Mark states that are accessible'''

    def _mark_states(statename: str) -> None:
        '''Recursively mark states that are accessible'''
        if statename in pool:
            pool.remove(statename)
            order.append(statename)
        state = _states[statename]
        dest_edges = [_transitions.transitions[edge] for edge in state.dest_edges]
        dest_states = [f'{a.scope}:{a.to_state}' for a in dest_edges]
        for substate in set(dest_states).intersection(pool):
            _mark_states(substate)

    _mark_states(statename)

    # Wildcard states
    for event in events:
        (from_state, to_state) = event.split('__')
        if '*' in from_state:
            for _state in list(pool):
                (_, state) = _state.split(':')
                if state == to_state:
                    pool.remove(_state)
                    order.append(_state)


def check_edges(_transitions: Transitions,
                events: Dict[str, List[str]],
                _events: Dict[str, Event]) -> None:
    '''Check that edges are valid'''

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
