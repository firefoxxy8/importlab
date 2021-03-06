"""Tests for output.py."""

import contextlib
import io
import unittest

from importlab import environment
from importlab import fs
from importlab import graph
from importlab import output
from importlab import utils


FILES = {
        "foo/a.py": "from . import b",
        "foo/b.py": "pass",
        "x.py": "import foo.a",
        "y.py": "import sys",
        "z.py": "import unresolved"
}


class TestOutput(unittest.TestCase):
    """Basic sanity tests for output methods."""

    def setUp(self):
        self.tempdir = utils.Tempdir()
        self.tempdir.setup()
        filenames = [
            self.tempdir.create_file(f, FILES[f])
            for f in FILES]
        self.fs = fs.OSFileSystem(self.tempdir.path)
        env = environment.Environment(fs.Path([self.fs]), (3, 6))
        self.graph = graph.ImportGraph.create(env, filenames)

    def tearDown(self):
        self.tempdir.teardown()

    def assertString(self, val):
        self.assertTrue(isinstance(val, str))

    def assertPrints(self, fn):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            fn(self.graph)
        self.assertTrue(out.getvalue())

    def test_inspect_graph(self):
        self.assertPrints(output.inspect_graph)

    def test_print_tree(self):
        self.assertPrints(output.print_tree)

    def test_print_topological_sort(self):
        self.assertPrints(output.print_topological_sort)

    def test_formatted_deps_list(self):
        self.assertString(output.formatted_deps_list(self.graph))

    def test_print_unresolved(self):
        self.assertPrints(output.print_unresolved_dependencies)


if __name__ == "__main__":
    unittest.main()
