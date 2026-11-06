"""Architectural guards: dependency direction and library hygiene."""

import ast
import pathlib

PKG = pathlib.Path(__file__).resolve().parent.parent

# Lower layers must not import higher ones. Modules on the same level must not import each other.
LEVELS = {
    'constants': 0, 'exceptions': 0, 'warnings_util': 0,
    'geometry': 1, 'layout': 1, 'dormer_geometry': 1, 'mesh': 1,
    'svgpath': 2, 'components': 2, 'joints': 2, 'formats3d': 2,
    'panel': 3, 'kerf': 3, 'placement': 3, 'cutouts': 3, 'casings': 3, 'patterns': 3,
    'render': 4, 'config': 4, 'mates': 4, 'builders.box': 4, 'builders.chimney': 4, 'builders.dormer': 4,
    'assembly': 5, 'placement3d': 5,
    'svg_generator': 6, 'model3d': 6,
    'maker': 7,
    '__init__': 8,
}


def _imports(path: pathlib.Path):
    tree = ast.parse(path.read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level >= 1:
            base = node.module or ''
            if node.level == 2:      # from ..x import y   (inside builders/)
                mods.add(base)
            elif base:
                mods.add(base)
            else:
                mods.update(a.name for a in node.names)
    return mods


def _module_name(path: pathlib.Path) -> str:
    return '.'.join(path.relative_to(PKG).with_suffix('').parts)


def test_every_module_has_a_layer():
    names = {_module_name(p) for p in PKG.glob('*.py') if p.name not in ('generate_house.py',)}
    names |= {_module_name(p) for p in (PKG / 'builders').glob('*.py') if p.name != '__init__.py'}
    assert names <= set(LEVELS), f"unassigned modules: {sorted(names - set(LEVELS))}"


def test_dependencies_point_downwards_only():
    violations = []
    files = [p for p in PKG.glob('*.py') if p.name != 'generate_house.py'] + \
            [p for p in (PKG / 'builders').glob('*.py') if p.name != '__init__.py']
    for path in files:
        me = _module_name(path)
        for dep in _imports(path):
            dep = dep.split('.')[0] if dep.split('.')[0] != 'builders' else dep
            if dep in LEVELS and LEVELS[dep] >= LEVELS[me]:
                violations.append(f"{me} (L{LEVELS[me]}) imports {dep} (L{LEVELS[dep]})")
    assert not violations, "\n".join(violations)


def test_library_does_not_print_or_import_in_functions():
    for path in list(PKG.glob('*.py')) + list((PKG / 'builders').glob('*.py')):
        if path.name == 'generate_house.py':
            continue
        tree = ast.parse(path.read_text())
        prints = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and getattr(n.func, 'id', None) == 'print']
        assert not prints, f"{path.name}: print() at lines {prints}"
        nested = [n.lineno for f in ast.walk(tree) if isinstance(f, (ast.FunctionDef,))
                  for n in ast.walk(f) if isinstance(n, (ast.Import, ast.ImportFrom))]
        assert not nested, f"{path.name}: function-level imports at lines {nested}"
