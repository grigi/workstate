'''WorkState test suite'''
import os
import subprocess
import uuid

from workstate.docgen import Digraph
from workstate.engine import Engine, Scope, BrokenStateModelException, trigger

import unittest

# pylint: disable=C1001,W0232,C0111,R0903

"""
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
        propose = "Propose the draft for review", ['draft__proposed']
        approve = ['proposed__approved']
        reject = ['proposed__draft']
        cancel = ['*__canceled'], "Cancel the chapter"

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

    class Triggers:
        @trigger('all_approved', ['chapter:approved'])
        def publish_book(self):
            'Publishes book if all chapters are approved'
            for chapter in self.get_chapter():
                if chapter.state != 'approved':
                    return False
            return True

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
#print(Chapter.graph())
Chapter.graph().render('chapter.png')
#pprint(Book.get_parsed())
Book.validate()
#print(Book.graph())
Book.graph().render('book.png')
BookEngine.validate()
#print(BookEngine.graph())
BookEngine.graph().render('bookengine.png')
"""


def clean_dot(dot: Digraph) -> set[str]:
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

        states = Scope1.get_parsed()['states'].states
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
        result = subprocess.Popen(['file', fname], stdout=subprocess.PIPE).communicate()[0]
        os.remove(fname)
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
                def check_complete(self):
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
        result = subprocess.Popen(['file', fname], stdout=subprocess.PIPE).communicate()[0]
        os.remove(fname)
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


if __name__ == '__main__':
    unittest.main()
