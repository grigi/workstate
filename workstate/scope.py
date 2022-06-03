'''WorkState engine'''
from __future__ import annotations

from typing import Dict, List

from workstate.docgen import BGCOLORS, FGCOLORS, Digraph
from workstate.engine_graph import Events, State, States, Transitions, Triggers, _Parsed
from workstate.exceptions import BrokenStateModelException
from workstate.utils import check_edges, mark_states


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

        check_edges(_transitions, events, _events)

        # Check that all states are connected
        initial = cls.get_initial()
        if initial:
            # Only check the local scope
            pool = {_state for _state in _states.keys() if _state.startswith(f'{scope}:')}
            order: List[str] = []

            mark_states(_states, _transitions, f'{scope}:{initial}', pool, order, events)

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
        order: List[str] = []
        transitions = cls.get_parsed().transitions
        scope = cls.get_scope()
        events = cls.get_event_map()

        mark_states(states, transitions, f'{scope}:{initial}', pool, order, events)

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
            return f'{scope or cls.get_scope()}:{val}'

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
                            pretty = f'{pevent} <SUP><FONT POINT-SIZE="10">({tname})</FONT></SUP>'
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
            return f'{cls.get_scope()}:{val}'

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
                                    f'<FONT POINT-SIZE="10">{tname}</FONT>',
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
