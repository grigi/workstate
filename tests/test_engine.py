'''WorkState test Engine'''
import os
import subprocess
import unittest
import uuid
from typing import Set

from workstate.docgen import Digraph
from workstate.engine import BrokenStateModelException, Engine, Scope, trigger

# pylint: disable=C0111,R0903,W0612,C0104


def clean_dot(dot: Digraph) -> Set[str]:
    '''Cleans out formatting from dot input'''
    return {
        val.split('[')[0].replace('"', '').strip()
        for val in dot.body
        if '\t' in val
    }


class EngineTest(unittest.TestCase):
    '''Tests basic Engine constructs'''

    def test_empty_engine(self):
        '''Engine: Empty'''
        with self.assertRaisesRegex(BrokenStateModelException, "Engine needs scopes"):

            class TestEngine(Engine):
                pass

    def test_engine_scope_non_list(self):
        '''Engine: scopes not in a List'''
        with self.assertRaisesRegex(BrokenStateModelException, "Engine needs scopes"):

            class TestEngine(Engine):
                scopes = "moo"

    def test_engine_scope_non_scopes(self):
        '''Engine: List doesn't contain Scopes'''
        with self.assertRaisesRegex(BrokenStateModelException, "Engine needs scopes"):

            class TestEngine(Engine):
                scopes = ["moo"]

    def test_scope_edge_event_engine_equal(self):
        '''Engine: Wrapping a Scope in an Engine results in no change in model'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']

        Scope1.validate()
        val1 = clean_dot(Scope1.graph())

        class TestEngine(Engine):
            scopes = [Scope1]

        val2 = clean_dot(TestEngine.graph())
        self.assertEqual(val1, val2)

    def test_two_scopes(self):
        '''Engine: Merging two Scopes'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']

        class Scope2(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']

        class TestEngine(Engine):
            scopes = [Scope1, Scope2]

        self.assertEqual(
            clean_dot(TestEngine.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:first -> scope1:second',
                'scope2:first',
                'scope2:second',
                'scope2:first -> scope2:second',
            },
        )

    def test_engine_generate_png(self):
        '''Engine: Generate PNG graph'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']
                gaa = ['*__third']

        Scope1.validate()

        class TestEngine(Engine):
            scopes = [Scope1]

        fname = f'/tmp/{uuid.uuid4()}.png'
        TestEngine.graph().render(fname)
        with subprocess.Popen(['file', fname], stdout=subprocess.PIPE) as pipe:
            result = pipe.communicate()[0]
        os.remove(fname)  # pylint: disable=no-member
        self.assertIn('PNG image', result.decode('UTF-8'))

    def test_engine_auto_validation(self):
        '''Engine: Validations always run on Engine creation'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second']
                gaa = ['fourth__third']

        with self.assertRaisesRegex(BrokenStateModelException, 'States.*not reachable'):

            class TestEngine(Engine):
                scopes = [Scope1]

    @unittest.expectedFailure
    def test_cross_scope_state_names(self):
        '''Engine: Cross-scope state names'''

        class Scope1(Scope):
            initial = 'first'

        class Scope2(Scope):
            initial = 'first'

            class Events:
                goo = ['first__second', 'scope1:first__second']

        class TestEngine(Engine):
            scopes = [Scope1, Scope2]

        self.assertEqual(
            clean_dot(TestEngine.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:first -> scope1:second',
                'scope2:first',
                'scope2:second',
                'scope2:first -> scope2:second',
            },
        )

    def test_cross_scope_trigger_edges(self):
        '''Engine: Cross-scope trigger edges'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                foo = ['first__second']

        class Scope2(Scope):
            initial = 'first'

            class Events:
                bar = ['first__second', 'second__third']

            class Triggers:
                @trigger('bar', ['scope1:second'])
                def justdoit(self):
                    return True

        class TestEngine(Engine):
            scopes = [Scope1, Scope2]

        self.assertEqual(
            clean_dot(TestEngine.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:first -> scope1:second',
                'scope2:first',
                'scope2:second',
                'scope2:third',
                'scope2:first -> scope2:second',
                'scope2:second -> scope2:third',
                'scope1:second -> scope2:second',
                'scope1:second -> scope2:third',
            },
        )

    @unittest.expectedFailure
    def test_cross_scope_trigger_events(self):
        '''Engine: Cross-scope trigger events'''

        class Scope1(Scope):
            initial = 'first'

            class Events:
                foo = ['first__second']

            class Triggers:
                @trigger('bar', ['second'])
                def justdoit(self):
                    return True

        class Scope2(Scope):
            initial = 'first'

            class Events:
                bar = ['first__second']

        class TestEngine(Engine):
            scopes = [Scope1, Scope2]

        self.assertEqual(
            clean_dot(TestEngine.graph()),
            {
                'scope1:first',
                'scope1:second',
                'scope1:first -> scope1:second',
                'scope2:first',
                'scope2:second',
                'scope2:first -> scope2:second',
                'scope1:second -> scope2:second',
            },
        )
