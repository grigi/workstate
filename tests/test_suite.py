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
