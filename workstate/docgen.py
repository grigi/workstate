'''Documentation generation module for WorkState'''
import subprocess

FGCOLORS = ['#333333', '#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d']
BGCOLORS = ['#dddddd', '#b3e2cd', '#fdcdac', '#cbd5e8', '#f4cae4', '#e6f5c9', '#fff2ae', '#f1e2cc']


class Digraph(object):
    '''Builds a GraphViz digraph'''

    def __init__(self):
        self.body = []

    def attributes(self, label, kwargs): #pylint: disable=R0201
        '''Return assembled DOT attributes string.'''
        result = []

        if label:
            result.append('label="%s"' % label)

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
        return 'digraph {\nrankdir="LR"\ndpi=120\n' + '\n'.join(self.body) + '\n}'

    def render(self, filename):
        '''Renders graph to filename as a PNG'''
        data = str(self).encode('utf-8')
        proc = subprocess.Popen(['dot', '-Tpng'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        image = proc.communicate(input=data)[0]
        outf = open(filename, 'wb')
        outf.write(image)
        outf.close()

def scope_graph(scope, dot=None, col=0, trigger_edges=False):
    '''Generates dot graph for provided scope'''

    def canon(val):
        '''Returns canonical edge name'''
        return scope.scope+':'+val

    if not dot:
        dot = Digraph()
    wildcards = set()
    events = scope.get_event_map()

    for state in scope.order_states():
        pretty = state.replace('_', ' ').title()
        if state == scope.initial:
            dot.node(canon(state), "*"+pretty, shape='oval', rank="max", style="bold,filled", fillcolor=BGCOLORS[col], color=FGCOLORS[col])
        else:
            dot.node(canon(state), pretty, shape='rectangle', style="filled,rounded", fillcolor=BGCOLORS[col], color=FGCOLORS[col])
    for edge in scope.transitions.values():
        if edge.from_state != '*':
            for event in events[edge.transitions[0]]:
                dot.edge(canon(edge.from_state), canon(edge.to_state), event, color=FGCOLORS[col])
        else:
            wildcards.add(edge.to_state)

    if wildcards:
        dot.node(canon('*'), 'Any', shape='none', style="filled", fillcolor=BGCOLORS[col], color=FGCOLORS[col])
        for dest in wildcards:
            for event in events['%s:*->%s' % (scope.scope, dest)]:
                dot.edge(canon('*'), canon(dest), event, color=FGCOLORS[col])

    return dot

def engine_graph(engine):
    '''Generates dot graph for whole engine'''

    dot = Digraph()

    for idx, scope in enumerate(engine.scopes.values()):
        #dot.body.append('subgraph {')
        scope_graph(scope, dot, col=idx+1, trigger_edges=True)
        #dot.body.append('}')

    return dot
