'''Documentation generation module for WorkState'''
import subprocess

FGCOLORS = ['#333333', '#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d']
BGCOLORS = ['#dddddd', '#b3e2cd', '#fdcdac', '#cbd5e8', '#f4cae4', '#e6f5c9', '#fff2ae', '#f1e2cc']


class Digraph:
    '''Builds a GraphViz digraph'''

    def __init__(self):
        self.body = []

    def attributes(self, label, kwargs): #pylint: disable=R0201
        '''Return assembled DOT attributes string.'''
        result = []

        if label:
            result.append('label=<%s>' % label)

        if kwargs:
            result.extend(['%s="%s"' % (k, v) for k, v in sorted(kwargs.items()) if v])

        if result:
            return ' [%s]' % ' '.join(result)
        return ''

    def node(self, name, label=None, **kwargs):
        '''Add a node'''
        self.body.append('\t"%s"%s' % (name, self.attributes(label, kwargs)))

    def edge(self, tail_name, head_name, label=None, **kwargs):
        '''Add an edge'''
        self.body.append('\t\t"%s" -> "%s"%s' % (tail_name, head_name, self.attributes(label, kwargs)))

    def __str__(self):
        return 'digraph {\nrankdir="LR"\ndpi=120\noverlap_shrink=true\noverlap=prism0\nsize=12\n' + '\n'.join(self.body) + '\n}'

    def render(self, filename):
        '''Renders graph to filename as a PNG'''
        data = str(self).encode('utf-8')
        proc = subprocess.Popen(['dot', '-Tpng'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        image = proc.communicate(input=data)[0]
        outf = open(filename, 'wb')
        outf.write(image)
        outf.close()

