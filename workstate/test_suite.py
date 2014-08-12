'''WorkState test suite'''
import os
import subprocess
import uuid
from pprint import pprint

from workstate.engine2 import *#Engine, Scope, trigger

try:
    import unittest2 as unittest #pylint: disable=F0401
except ImportError:
    import unittest



class Chapter(Scope):
    'A chapter'
    # pylint: disable=E1101,R0903,C1001,C0111,W0232
    initial = 'draft'

    class States:
        draft = 'The chapter is being written'
        proposed = 'The chapter is proposed for apprval'
        approved = 'The chapter is approved'
        canceled = 'The chapter is canceled'

    class Transitions:
        draft__proposed = 'Request chapter approval'
        proposed__draft = 'Chapter declined'
        __canceled = 'Chapter canceled'

        def proposed__approved(self):
            'Chapter approved'
            return self.marked

    class Events:
        propose = ['draft__proposed']
        approve = ['proposed__approved']
        reject = ['proposed__draft']
        cancel = ['*__canceled']

    class Triggers:
        @trigger('reject', ['proposed'])
        def check_complete(self):
            'Rejects chapter if not complete when landing at proposed state'
            return not self.complete

    # pylint: enable=E1101,R0903,C1001,C0111,W0232

    def __init__(self, book):
        self.book = book
        self.marked = False
        self.complete = False
        book.add_chapter(self)

    def get_book(self):
        'Returns list of books'
        return [self.book]


class Book(Scope):
    'A book'
    # pylint: disable=E1101,R0903,C1001,C0111,W0232
    initial = 'draft'

    class States:
        draft = 'Book is being written'
        published = 'Book is done'
        canceled = 'The Book is canceled'

    class Transitions:
        draft__published = 'All chapters are approved'
        __canceled = 'Book canceled'

    class Events:
        all_approved = ['draft__published']
        cancel = ['*__canceled']

    '''class Triggers:
        @trigger('all_approved', ['chapter:approved'])
        def publish_book(self):
            'Publishes book if all chapters are approved'
            for chapter in self.get_chapter():
                if chapter.state != 'approved':
                    return False
            return True'''

    # pylint: enable=E1101,R0903,C1001,C0111,W0232

    def __init__(self):
        self.chapters = []

    def add_chapter(self, chapter):
        self.chapters.append(chapter)

    def get_chapter(self):
        'Returns list of chapters'
        return self.chapters


class BookEngine(Engine):
    scopes = [Book, Chapter]

#pprint(Chapter.get_parsed())
Chapter.validate()
print(Chapter.graph())
Chapter.graph().render('chapter.png')
#pprint(Book.get_parsed())
Book.validate()
print(Book.graph())
Book.graph().render('book.png')
print(BookEngine.graph())
BookEngine.graph().render('bookengine.png')


"""
'''engine = Engine()
quote = engine.scope('quote', initial='draft')
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

scope1 = engine.scope('scope1', initial='first')
scope1.add_transition('first', 'second')
scope2 = engine.scope('scope2', initial='first')
scope2.add_transition('first', 'second')
engine.add_event('go', ['scope1:first->second', 'scope2:first->second'])


engine.validate()

#pprint(engine.dict())

scope_graph(quote).render('quote.png')
engine.graph().render('engine.png')'''


engine = Engine()
doc = engine.scope('doc', initial='draft')

def check_marked(obj):
    return obj.get('marked', False)

doc.add_transition('proposed', 'approved', condition=check_marked)
doc.add_transition('draft', 'proposed')
doc.add_transition('proposed', 'draft')

engine.add_event('propose', ['doc:draft->proposed'])
engine.add_event('approve', ['doc:proposed->approved'])
engine.add_event('reject', ['doc:proposed->draft'])

def check_complete(obj):
    return obj.get('complete', False)

engine.add_trigger('reject', ['doc:proposed'], condition=check_complete)

def get_doc_state(obj):
    return obj.get('state', doc.initial)

def set_doc_state(obj, state):
    obj['state'] = state

doc.set_state_property(get_doc_state, set_doc_state)
#doc.set_state_property(
    #lambda obj: obj.get('state', doc.initial),  # getter
    #lambda obj: obj['state'] = state            # setter
#)

engine.validate()
pprint(engine.dict())
#doc.graph().render('quote.png')
print engine.graph()#.render('engine.png')

def clean_dot(dot):
    '''Cleans out formatting from dot input'''
    return set([val.split('[')[0].replace('"', '').strip() for val in dot.body])

class WorkState(unittest.TestCase):
    '''Tests basic WorkState constructs'''

    def test_empty_engine(self):
        engine = Engine()
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set())

    def test_empty_scope(self):
        engine = Engine()
        scope1 = engine.scope('scope1')
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set())
        self.assertEqual(clean_dot(scope1.graph()), set())

    def test_initial_scope(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set([
            'scope1:first',
        ]))
        self.assertEqual(clean_dot(scope1.graph()), clean_dot(engine.graph()))

    def test_scope_edge_event(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        with self.assertRaisesRegexp(Exception, 'Transition.*has no events'):
            engine.validate()
        engine.add_event('go', ['scope1:first->second'])
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set([
            'scope1:first',
            'scope1:second',
            'scope1:first -> scope1:second',
        ]))

    def test_scope_loose_states(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope1.add_transition('third', 'fourth')
        engine.add_event('go', ['scope1:first->second', 'scope1:third->fourth'])
        with self.assertRaisesRegexp(Exception, 'States.*not reachable'):
            engine.validate()

    def test_two_scopes(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope2 = engine.scope('scope2', initial='first')
        scope2.add_transition('first', 'second')
        engine.add_event('go', ['scope1:first->second', 'scope2:first->second'])
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set([
            'scope1:first',
            'scope1:second',
            'scope1:first -> scope1:second',
            'scope2:first',
            'scope2:second',
            'scope2:first -> scope2:second',
        ]))

    def test_wildcard_edge(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope1.add_transition('*', 'third')
        engine.add_event('go', ['scope1:first->second'])
        engine.add_event('goo', ['scope1:*->third'])
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set([
            'scope1:first',
            'scope1:second',
            'scope1:third',
            'scope1:*',
            'scope1:first -> scope1:second',
            'scope1:* -> scope1:third',

        ]))

    def test_event_already_defined(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        engine.add_event('go', ['scope1:first->second'])
        # don't fail here
        engine.add_event('moo', ['scope1:first->second'])
        # fail here
        with self.assertRaisesRegexp(Exception, 'Event go already defined'):
            engine.add_event('go', ['scope1:first->second'])

    def test_event_bad_transition(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
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
        scope1 = engine.scope('scope1', initial='first', states=states)
        self.assertEqual(set(states.keys()), set(scope1.states.keys()))
        for key, val in scope1.states.items():
            # check that docs got transferred
            self.assertEqual(val.doc, states[key])

    def test_listed_transition(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'third')
        scope1.add_transition(['first', 'third'], 'second')
        engine.add_event('bad', ['scope1:first->third'])
        engine.add_event('go', ['scope1:first->second', 'scope1:third->second'])
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set([
            'scope1:first',
            'scope1:second',
            'scope1:third',
            'scope1:first -> scope1:second',
            'scope1:first -> scope1:third',
            'scope1:third -> scope1:second',
        ]))

    def test_validator_handles_loops(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'first')
        scope1.add_transition('second', 'third')
        scope1.add_transition(['first', 'third'], 'second')
        engine.add_event('delay', ['scope1:first->first'])
        engine.add_event('retry', ['scope1:second->third'])
        engine.add_event('go', ['scope1:first->second', 'scope1:third->second'])
        engine.validate()
        self.assertEqual(clean_dot(engine.graph()), set([
            'scope1:first',
            'scope1:second',
            'scope1:third',
            'scope1:first -> scope1:second',
            'scope1:first -> scope1:first',
            'scope1:third -> scope1:second',
            'scope1:second -> scope1:third',
        ]))

    def test_duplicate_transition(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        with self.assertRaisesRegexp(Exception, "Transition.*already defined"):
            scope1.add_transition('first', 'second')

    def test_duplicate_transition_wildcard(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        with self.assertRaisesRegexp(Exception, "Transition.*already defined"):
            scope1.add_transition('*', 'second')

    def test_generate_png(self):
        engine = Engine()
        scope1 = engine.scope('scope1', initial='first')
        scope1.add_transition('first', 'second')
        scope1.add_transition('*', 'third')
        engine.add_event('go', ['scope1:first->second'])
        engine.add_event('goo', ['scope1:*->third'])
        engine.validate()
        fname = '/tmp/%s.png' % uuid.uuid4()
        engine.graph().render(fname)
        result = subprocess.Popen(['file', fname], stdout=subprocess.PIPE).communicate()[0]
        os.remove(fname)
        self.assertIn('PNG image', result.decode('UTF-8'))

if __name__ == '__main__':
    unittest.main()
"""
