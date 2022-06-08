'''WorkState test Scope'''
import os
import subprocess
import unittest
import uuid
from typing import Set

from workstate.docgen import Digraph
from workstate.engine import BrokenStateModelException, Scope, trigger

# pylint: disable=C0111,R0903


def clean_dot(dot: Digraph) -> Set[str]:
    '''Cleans out formatting from dot input'''
    return {
        val.split('[')[0].replace('"', '').strip()
        for val in dot.body
        if '\t' in val
    }


class ScopeTest(unittest.TestCase):
    '''Tests basic Scope constructs'''

    def test_empty_scope(self):
        '''Scope: Empty'''

        class Scope1(Scope):
            pass

        Scope1.validate()
        self.assertEqual(clean_dot(Scope1.graph()), set())

    def test_initial_scope(self):
        '''Scope: Initial only'''

        class Scope1(Scope):
            initial = 'first'

        Scope1.validate()
        self.assertEqual(clean_dot(Scope1.graph()), {'scope1:first'})

    def test_scope_edge_noevent(self):
        '''Scope: Edge without event'''

        class Scope1(Scope):
            initial = 'first'

            class Transitions:
                first__second = 'Some sample transition'

        with self.assertRaisesRegex(BrokenStateModelException, 'Transition.*has no events'):
            Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {'scope1:first', 'scope1:second', 'scope1:first -> scope1:second'},
        )

    def test_scope_edge_event(self):
        '''Scope: Edge with event'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']

        Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {'scope1:first', 'scope1:second', 'scope1:first -> scope1:second'},
        )

    def test_scope_loose_states(self):
        '''Scope: Disconnected states'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second', 'third__fourth']

        with self.assertRaisesRegex(BrokenStateModelException, 'States.*not reachable'):
            Scope1.validate()

    def test_wildcard_edge(self):
        '''Scope: Wildcard edge'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']
                gaa = ['*__third']

        Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:third',
                'scope1:*',
                'scope1:first -> scope1:second',
                'scope1:* -> scope1:third',
            },
        )

    def test_define_states(self):
        '''Scope: Defining states'''

        class Scope1(Scope):
            initial = 'first'

            class States:
                first = 'The first'
                second = 'The second'
                do_it = 'Yup, you gotta DO it'

        states = Scope1.get_parsed().states.states
        # Check that states are there
        self.assertEqual(set(states.keys()), {'scope1:first', 'scope1:second', 'scope1:do_it'})
        # Check that docs got transferred
        self.assertEqual(
            {a.doc for a in states.values()},
            {'The first', 'The second', 'Yup, you gotta DO it'},
        )
        # Of course validation should fail as this is an incomplete scope
        with self.assertRaisesRegex(BrokenStateModelException, 'States.*not reachable'):
            Scope1.validate()

    def test_listed_transition(self):
        '''Scope: Defining many transitions in one List'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                bad = ['first__third']
                goo = ['first__second', 'third__second']

        Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:third',
                'scope1:first -> scope1:second',
                'scope1:first -> scope1:third',
                'scope1:third -> scope1:second',
            },
        )

    def test_validator_handles_loops(self):
        '''Scope: Validator doesn't choke on loops'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                delay = ['first__first']
                retry = ['second__third']
                goo = ['first__second', 'third__second']

        Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:third',
                'scope1:first -> scope1:second',
                'scope1:first -> scope1:first',
                'scope1:third -> scope1:second',
                'scope1:second -> scope1:third',
            },
        )

    def test_scope_generate_png(self):
        '''Scope: Generate PNG graph'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']
                gaa = ['*__third']

        Scope1.validate()
        fname = f'/tmp/{uuid.uuid4()}.png'
        Scope1.graph().render(fname)
        with subprocess.Popen(['file', fname], stdout=subprocess.PIPE) as pipe:
            result = pipe.communicate()[0]
        os.remove(fname)  # pylint: disable=no-member
        self.assertIn('PNG image', result.decode('UTF-8'))

    def test_conditional_transition(self):
        '''Scope: Conditional transitions'''

        class Scope1(Scope):
            initial = 'first'

            class Transitions:
                def first__second(self):
                    '''A Conditional transition'''
                    return False

        with self.assertRaisesRegex(BrokenStateModelException, 'Transition.*has no events'):
            Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {'scope1:first', 'scope1:second', 'scope1:first -> scope1:second'},
        )

    def test_scoped_state_names(self):
        '''Scope: scoped and unscoped state names'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                bad = ['first__second']
                goo = ['scope1:second__third']

        Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:third',
                'scope1:first -> scope1:second',
                'scope1:second -> scope1:third',
            },
        )

    def test_scoped_transition_names(self):
        '''Scope: scoped and unscoped transition names'''

        class Scope1(Scope):
            class Events:
                bad = ['first__second']
                goo = ['scope2:second__third']

        Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope2:second',
                'scope2:third',
                'scope1:first -> scope1:second',
                'scope2:second -> scope2:third',
            },
        )

    def test_missing_event_trigger(self):
        '''Scope: Missing event on trigger'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                bad = ['first__second']

            class Triggers:
                @trigger('goo', ['second'])
                def check_complete(self) -> bool:
                    return True

        with self.assertRaisesRegex(BrokenStateModelException, "Event.*contains no transitions"):
            Scope1.validate()

    def test_basic_trigger(self):
        '''Scope: Basic trigger-next event'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                bad = ['first__second']
                goo = ['second__third']

            class Triggers:
                @trigger('goo', ['second'])
                def check_complete(self):
                    return True

        Scope1.validate()
        self.assertEqual(
            clean_dot(Scope1.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:third',
                'scope1:first -> scope1:second',
                'scope1:second -> scope1:third',
            },
        )
