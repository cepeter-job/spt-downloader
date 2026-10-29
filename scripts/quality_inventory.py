"""Repeatable source-only AST inventory; never import or execute product modules."""
import argparse
import ast
import json
from pathlib import Path
import subprocess

def inventory(root, revision='HEAD'):
    """Parse immutable Git bytes so dirty/deleted files cannot alter this audit."""
    commit = subprocess.check_output(
        ['git', 'rev-parse', '--verify', revision + '^{commit}'], cwd=root, text=True).strip()
    names = subprocess.check_output(
        ['git', 'ls-tree', '-r', '-z', '--name-only', commit], cwd=root).decode('utf-8')
    paths = [Path(p) for p in names.split('\0') if p.endswith('.py')]
    result = {'revision': commit, 'source_kind': 'git-commit', 'functions': [], 'catches': [], 'skips': []}
    class Scan(ast.NodeVisitor):
        def __init__(self, path):
            self.path, self.scope = path.as_posix(), []
        def visit_ClassDef(self, node):
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()
        def visit_FunctionDef(self, node):
            def owned(n):
                for child in ast.iter_child_nodes(n):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                        continue
                    yield child
                    yield from owned(child)
            nodes = list(owned(node))
            complexity = 1 + sum(isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.comprehension)) for n in nodes)
            complexity += sum(len(n.values)-1 for n in nodes if isinstance(n, ast.BoolOp))
            complexity += sum(len(n.cases) for n in nodes if isinstance(n, ast.Match))
            self.scope.append(node.name)
            result['functions'].append({'file': self.path, 'name': '.'.join(self.scope), 'line': node.lineno, 'lines': node.end_lineno-node.lineno+1, 'complexity': complexity, 'documented': ast.get_docstring(node) is not None, 'public': not node.name.startswith('_'), 'top_level': len(self.scope)==1})
            self.generic_visit(node)
            self.scope.pop()
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ExceptHandler(self, node):
            label = ast.unparse(node.type) if node.type else 'bare'
            if node.type is None or any(isinstance(n, ast.Name) and n.id in ('Exception', 'BaseException') for n in ast.walk(node.type)):
                result['catches'].append({'file': self.path, 'name': '.'.join(self.scope), 'line': node.lineno, 'type': label, 'body': ast.unparse(node)})
            self.generic_visit(node)
        def visit_Call(self, node):
            name = ast.unparse(node.func)
            if name in ('pytest.skip', 'pytest.importorskip', 'pytest.xfail', 'pytest.mark.skip', 'pytest.mark.skipif', 'pytest.mark.xfail'):
                result['skips'].append({'file': self.path, 'name': '.'.join(self.scope), 'line': node.lineno, 'call': ast.unparse(node)})
            self.generic_visit(node)
    for path in paths:
        source = subprocess.check_output(
            ['git', 'show', commit + ':' + path.as_posix()], cwd=root).decode('utf-8-sig')
        Scan(path).visit(ast.parse(source))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--revision', default='HEAD', help='Immutable commit/ref to inspect, default HEAD.')
    args = parser.parse_args()
    result = inventory(Path(__file__).resolve().parents[1], args.revision)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({key:len(result[key]) for key in ('functions','catches','skips')}))


if __name__ == '__main__':
    main()
