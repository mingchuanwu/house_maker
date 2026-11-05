"""Mini mutation tester: mutate one AST site at a time in a COPY of the package and run the suite."""
import ast, copy, json, os, shutil, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = '/tmp/mut/work'
TARGETS = sys.argv[1].split(',')          # file.py or file.py:FIRST-LAST (line range)
PYTEST_ARGS = os.environ.get('MUT_PYTEST_ARGS', 'tests').split()
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 1     # one test process at a time unless asked
MAX_WORKERS = 3                                              # each worker runs a numpy-heavy test suite: keep memory modest
if WORKERS > MAX_WORKERS and not os.environ.get('MUT_ALLOW_MANY'):
    sys.exit(f'refusing to start {WORKERS} workers (limit {MAX_WORKERS}); each runs a full test process. '
             f'Set MUT_ALLOW_MANY=1 only if you know the machine has the memory.')

SWAP_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
SWAP_CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}

class Sites(ast.NodeVisitor):
    def __init__(self): self.sites = []
    def generic_visit(self, node):
        if isinstance(node, ast.BinOp) and type(node.op) in SWAP_BIN: self.sites.append((node, 'binop'))
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in SWAP_CMP: self.sites.append((node, 'cmp'))
        elif isinstance(node, ast.BoolOp): self.sites.append((node, 'boolop'))
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool): self.sites.append((node, 'num'))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool): self.sites.append((node, 'bool'))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): self.sites.append((node, 'not'))
        super().generic_visit(node)

def in_docstring_or_fmt(tree):
    skip = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            for c in ast.walk(n): skip.add(id(c))
    return skip

class Apply(ast.NodeTransformer):
    def __init__(self, target): self.target, self.done = target, False
    def visit(self, node):
        if node is self.target and not self.done:
            self.done = True
            if isinstance(node, ast.BinOp): node.op = SWAP_BIN[type(node.op)]()
            elif isinstance(node, ast.Compare): node.ops = [SWAP_CMP[type(node.ops[0])]()]
            elif isinstance(node, ast.BoolOp): node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            elif isinstance(node, ast.Constant) and isinstance(node.value, bool): node.value = not node.value
            elif isinstance(node, ast.Constant): v = node.value; node.value = (v + 1) if v in (0, 0.0) else (v * 2 if v != 1 else 2)
            elif isinstance(node, ast.UnaryOp): return node.operand
            return node
        return super().visit(node)

def enumerate_mutants(spec):
    rel, _, rng = spec.partition(':')
    lo, hi = (map(int, rng.split('-')) if rng else (0, 10 ** 9))
    src = open(os.path.join(SRC, rel)).read(); tree = ast.parse(src)
    skip = in_docstring_or_fmt(tree); v = Sites(); v.visit(tree)
    out = []
    for i, (node, kind) in enumerate(v.sites):
        if id(node) in skip or not (lo <= node.lineno <= hi): continue
        out.append((rel, i, kind, node.lineno, ast.unparse(node)[:90]))
    return out

def make_workdir(w):
    d = f'{ROOT}/w{w}/house_maker'
    if os.path.exists(d): return d
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copytree(SRC, d, ignore=shutil.ignore_patterns('.venv', 'node_modules', 'dist', 'build', '.git', '__pycache__', '*.egg-info', '.pytest_cache'))
    nm = os.path.join(SRC, 'node_modules')
    if os.path.exists(nm): os.symlink(nm, os.path.join(d, 'node_modules'))
    return d

def run_chunk(args):
    w, mutants = args
    d = make_workdir(w); res = []
    for rel, idx, kind, line, _before in mutants:
        path = os.path.join(d, rel); orig = open(os.path.join(SRC, rel)).read()
        tree = ast.parse(orig); v = Sites(); v.visit(tree); skip = in_docstring_or_fmt(tree)
        node = v.sites[idx][0]
        before = ast.unparse(node)
        t = Apply(node); new = t.visit(tree); ast.fix_missing_locations(new)
        mutated = ast.unparse(new)
        after = ast.unparse(node) if not isinstance(node, ast.UnaryOp) else before
        open(path, 'w').write(mutated)
        status = 'survived'
        try:
            r = subprocess.run([sys.executable, '-m', 'pytest', '-x', '-q', '-p', 'no:cacheprovider', *PYTEST_ARGS], cwd=d,
                               capture_output=True, text=True, timeout=90, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            if r.returncode == 0: status = 'survived'
            elif r.returncode == 1: status = 'killed'          # tests failed
            else: status = 'error'                             # collection/usage error: not a real kill
        except subprocess.TimeoutExpired:
            status = 'killed'
        open(path, 'w').write(orig)
        rec = {'file': rel, 'line': line, 'kind': kind, 'before': before[:90], 'after': after[:90], 'status': status}
        res.append(rec)
        with open('/tmp/mut/results.jsonl', 'a') as log:          # incremental: survives an interrupted run
            log.write(json.dumps(rec) + '\n')
    return res

def _free_gb():
    """Free + inactive memory in GB (macOS vm_stat or /proc/meminfo); None if unknown."""
    try:
        if sys.platform == 'darwin':
            out = subprocess.run(['vm_stat'], capture_output=True, text=True).stdout
            page = int(out.split('page size of')[1].split('bytes')[0])
            pages = {l.split(':')[0]: int(l.split(':')[1].strip(' .\n')) for l in out.splitlines()[1:] if ':' in l}
            return (pages.get('Pages free', 0) + pages.get('Pages inactive', 0)) * page / 2 ** 30
        for l in open('/proc/meminfo'):
            if l.startswith('MemAvailable'):
                return int(l.split()[1]) / 2 ** 20
    except Exception:
        return None


if __name__ == '__main__':
    free = _free_gb()
    need = 1.5 * WORKERS
    if free is not None and free < need and not os.environ.get('MUT_IGNORE_MEMORY'):
        sys.exit(f'only {free:.1f} GB free, need about {need:.1f} GB for {WORKERS} worker(s); close applications or lower the workers')
    shutil.rmtree(ROOT, ignore_errors=True)          # always mutate a fresh copy of the current source
    os.makedirs('/tmp/mut', exist_ok=True)
    done = {}
    if os.environ.get('MUT_RESUME') and os.path.exists('/tmp/mut/results.jsonl'):
        for line in open('/tmp/mut/results.jsonl'):
            r = json.loads(line)
            if r['status'] != 'error':                      # interrupted runs are redone
                done[(r['file'], r['line'], r['kind'], r['before'])] = r
    else:
        open('/tmp/mut/results.jsonl', 'w').close()
    allm = [m for t in TARGETS for m in enumerate_mutants(t)]
    todo = [m for m in allm if (m[0], m[3], m[2], m[4]) not in done]
    print(f'{len(allm)} mutants over {len(TARGETS)} files; {len(done)} already done, {len(todo)} to run, {WORKERS} workers', flush=True)
    chunks = [(w, todo[w::WORKERS]) for w in range(WORKERS)]
    t0 = time.time(); results = []
    with ProcessPoolExecutor(WORKERS) as ex:
        for part in ex.map(run_chunk, chunks): results += part
    everything = [json.loads(l) for l in open('/tmp/mut/results.jsonl')]
    json.dump(everything, open('/tmp/mut/results.json', 'w'), indent=1)
    print(f'done in {time.time()-t0:.0f}s')
