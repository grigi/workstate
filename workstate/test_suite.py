'''WorkState test suite'''
import os
import subprocess
import uuid

from workstate.docgen import engine_graph, scope_graph
from workstate.engine import Engine, Scope

try:
    import unittest2 as unittest #pylint: disable=F0401
except ImportError:
    import unittest

#from pprint import pprint


'''engine = Engine()
quote = Scope(engine, 'quote', initial='draft')
quote.add_transition('in_progress', 'ready')
quote.add_transition(['draft', 'ready'], 'in_progress')
quote.add_transition('ready', 'done')
quote.add_transition('done', 'in_progress')
quote.add_transition('*', 'cancelled')

engine.add_event('edit', ['quote:done->in_progress', 'quote:draft->in_progress', 'quote:ready->in_progress'])
engine.add_event('moo', ['quote:draft->in_progress'])
engine.add_event('complete', ['quote:in_progress->ready'])
engine.add_event('finish', ['quote:ready->done'])
engine.add_event('cancel', ['quote:*->cancelled'])

scope1 = Scope(engine, 'scope1', initial='first')
scope1.add_transition('first', 'second')
scope2 = Scope(engine, 'scope2', initial='first')
scope2.add_transition('first', 'second')
engine.add_event('go', ['scope1:first->second', 'scope2:first->second'])


engine.validate()

#pprint(engine.dict())

scope_graph(quote).render('quote.png')
engine_graph(engine).render('engine.png')'''


def clean_dot(dot):
    '''Cleans out formatting from dot input'''
    return set([val.split('[')[0].replace('"', '').strip() for val in dot.body])

class WorkState(unittest.TestCase):
    '''Tests basic WorkState constructs'''

    def test_empty_engine(self):
        engine = Engine()
        engine.validate()
        self.assertEqual(clean_dot(engine_graph(engine)), set())

    def test_empty_scope(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1')
        engine.validate()
        self.assertEqual(clean_dot(engine_graph(engine)), set())
        self.assertEqual(clean_dot(scope_graph(scope1)), set())

    def test_initial_scope(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        engine.validate()
        self.assertEqual(clean_dot(engine_graph(engine)), set([
            'scope1:first',
        ]))
        self.assertEqual(clean_dot(scope_graph(scope1)), clean_dot(engine_graph(engine)))

    def test_scope_edge_event(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        with self.assertRaisesRegexp(Exception, 'Transition.*has no events'):
            engine.validate()
        engine.add_event('go', ['scope1:first->second'])
        engine.validate()
        self.assertEqual(clean_dot(engine_graph(engine)), set([
            'scope1:first',
            'scope1:second',
            'scope1:first -> scope1:second',
        ]))

    def test_scope_loose_states(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope1.add_transition('third', 'fourth')
        engine.add_event('go', ['scope1:first->second', 'scope1:third->fourth'])
        with self.assertRaisesRegexp(Exception, 'States.*not reachable'):
            engine.validate()

    def test_two_scopes(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope2 = Scope(engine, 'scope2', initial='first')
        scope2.add_transition('first', 'second')
        engine.add_event('go', ['scope1:first->second', 'scope2:first->second'])
        engine.validate()
        self.assertEqual(clean_dot(engine_graph(engine)), set([
            'scope1:first',
            'scope1:second',
            'scope1:first -> scope1:second',
            'scope2:first',
            'scope2:second',
            'scope2:first -> scope2:second',
        ]))

    def test_wildcard_edge(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope1.add_transition('*', 'third')
        engine.add_event('go', ['scope1:first->second'])
        engine.add_event('goo', ['scope1:*->third'])
        engine.validate()

    def test_event_already_defined(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        engine.add_event('go', ['scope1:first->second'])
        # don't fail here
        engine.add_event('moo', ['scope1:first->second'])
        # fail here
        with self.assertRaisesRegexp(Exception, 'Event go already defined'):
            engine.add_event('go', ['scope1:first->second'])

    def test_event_bad_transition(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        with self.assertRaisesRegexp(Exception, "Transition.*doesn't exist"):
            engine.add_event('go', ['scope1:first->second', 'scope1:bad->second'])

    def test_define_states(self):
        engine = Engine()
        states = {
            'first': 'The first',
            'second': 'The second',
            'do_it': 'Yup, you gotta DO it',
        }
        scope1 = Scope(engine, 'scope1', initial='first', states=states)
        self.assertEqual(set(states.keys()), set(scope1.states.keys()))
        for key, val in scope1.states.items():
            # check that docs got transferred
            self.assertEqual(val.doc, states[key])

    def test_listed_transition(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'third')
        scope1.add_transition(['first', 'third'], 'second')
        engine.add_event('bad', ['scope1:first->third'])
        engine.add_event('go', ['scope1:first->second', 'scope1:third->second'])
        engine.validate()

    def test_validator_handles_loops(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'first')
        scope1.add_transition('second', 'third')
        scope1.add_transition(['first', 'third'], 'second')
        engine.add_event('delay', ['scope1:first->first'])
        engine.add_event('retry', ['scope1:second->third'])
        engine.add_event('go', ['scope1:first->second', 'scope1:third->second'])
        engine.validate()

    def test_duplicate_transition(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        with self.assertRaisesRegexp(Exception, "Transition.*already defined"):
            scope1.add_transition('first', 'second')

    def test_duplicate_transition_wildcard(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        with self.assertRaisesRegexp(Exception, "Transition.*already defined"):
            scope1.add_transition('*', 'second')

    def test_generate_png(self):
        engine = Engine()
        scope1 = Scope(engine, 'scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope1.add_transition('*', 'third')
        engine.add_event('go', ['scope1:first->second'])
        engine.add_event('goo', ['scope1:*->third'])
        engine.validate()
        fname = '/tmp/%s.png' % uuid.uuid4()
        engine_graph(engine).render(fname)
        result = subprocess.Popen(['file', fname], stdout=subprocess.PIPE).communicate()[0]
        os.remove(fname)
        self.assertIn('PNG image', result.decode('UTF-8'))

if __name__ == '__main__':
    unittest.main()
