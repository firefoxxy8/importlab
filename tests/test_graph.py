"""Tests for graph.py."""

import unittest

from importlab import environment
from importlab import fs
from importlab import graph
from importlab import resolve
from importlab import utils


class TestCycle(unittest.TestCase):
    """Tests for Cycle."""

    def test_flatten(self):
        a = graph.Cycle([[1, 2], [2, 3], [3, 1]])
        b = graph.Cycle([[4, 5], [5, 4]])
        c = graph.Cycle([[a, 6], [6, b], [b, 7], [7, a]])
        nodes = c.flatten_nodes()
        self.assertEqual(sorted(nodes), [1, 2, 3, 4, 5, 6, 7])


class FakeImportGraph(graph.DependencyGraph):
    """An ImportGraph with file imports stubbed out.

    Also adds ordered_foo() wrappers around output methods to help in testing.
    """

    def __init__(self, deps):
        super(FakeImportGraph, self).__init__()
        self.deps = deps

    def get_source_file_provenance(self, filename):
        return resolve.Direct(filename, 'module.name')

    def get_file_deps(self, filename):
        if filename in self.deps:
            resolved, unresolved, provenance = self.deps[filename]
            self.provenance.update(provenance)
            return (resolved, unresolved)
        return ([], [])

    def ordered_deps_list(self):
        deps = []
        for k, v in self.deps_list():
            deps.append((k, sorted(v)))
        return list(sorted(deps))

    def ordered_sorted_source_files(self):
        return [list(sorted(x)) for x in self.sorted_source_files()]


# Deps = { file : ([resolved deps], [broken deps], {dep_file:provenance}) }

SIMPLE_DEPS = {
        "a.py": (["b.py", "c.py"], [],
                 {"b.py": resolve.Local("b.py", "b", "fs1"),
                  "c.py": resolve.Local("c.py", "c", "fs2")
                  }),
        "b.py": (["d.py"], ["e"],
                 {"d.py": resolve.System("d.py", "d")})
}

SIMPLE_CYCLIC_DEPS = {
        "a.py": (["b.py", "c.py"], ["e"], {}),
        "b.py": (["d.py", "a.py"], ["f"], {}),
}


class TestDependencyGraph(unittest.TestCase):
    """Tests for DependencyGraph."""

    def check_order(self, xs, *args):
        """Checks that args form an increasing sequence within xs."""
        indices = [xs.index(arg) for arg in args]
        for i in range(1, len(indices)):
            self.assertTrue(indices[i - 1] < indices[i],
                            "%s comes before %s" % (args[i], args[i - 1]))

    def test_simple(self):
        g = FakeImportGraph(SIMPLE_DEPS)
        g.add_file_recursive("a.py")
        g.build()
        self.assertEqual(g.ordered_deps_list(), [
            ("a.py", ["b.py", "c.py"]),
            ("b.py", ["d.py"]),
            ("c.py", []),
            ("d.py", [])])
        self.assertEqual(g.get_all_unresolved(), set(["e"]))
        sources = g.ordered_sorted_source_files()
        self.check_order(sources, ["d.py"], ["b.py"], ["a.py"])
        self.check_order(sources, ["c.py"], ["a.py"])
        self.assertEqual(sorted(g.provenance.keys()),
                         ["a.py", "b.py", "c.py", "d.py"])
        # a.py is a directly added source
        provenance = g.provenance["a.py"]
        self.assertTrue(isinstance(provenance, resolve.Direct))
        self.assertEqual(provenance.module_name, 'module.name')
        # b.py came from fs1
        self.assertEqual(g.provenance["b.py"].fs, "fs1")

    def test_simple_cycle(self):
        g = FakeImportGraph(SIMPLE_CYCLIC_DEPS)
        g.add_file_recursive("a.py")
        g.build()
        cycles = [x for x, ys in g.deps_list()
                  if isinstance(x, graph.NodeSet)]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0].nodes), set(["a.py", "b.py"]))
        self.assertEqual(g.get_all_unresolved(), set(["e", "f"]))
        sources = g.ordered_sorted_source_files()
        self.check_order(sources, ["d.py"], ["a.py", "b.py"])
        self.check_order(sources, ["c.py"], ["a.py", "b.py"])


FILES = {
        "foo/a.py": "from . import b",
        "foo/b.py": "pass",
        "x.py": "import foo.a"
}


class TestImportGraph(unittest.TestCase):
    """Tests for ImportGraph."""

    def setUp(self):
        self.tempdir = utils.Tempdir()
        self.tempdir.setup()
        self.filenames = [
            self.tempdir.create_file(f, FILES[f])
            for f in FILES]
        self.fs = fs.OSFileSystem(self.tempdir.path)
        self.env = environment.Environment(fs.Path([self.fs]), (3, 6))

    def tearDown(self):
        self.tempdir.teardown()

    def test_basic(self):
        g = graph.ImportGraph.create(self.env, self.filenames)
        self.assertEqual(
                g.sorted_source_files(),
                [[self.tempdir[x]] for x in ["foo/b.py", "foo/a.py", "x.py"]])


if __name__ == "__main__":
    unittest.main()
