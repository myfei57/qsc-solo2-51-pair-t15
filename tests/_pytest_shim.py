"""Minimal pytest stand-in so the suite can run without pytest installed.

Implements just the subset the suite uses: ``raises``, ``fixture``,
``parametrize``/``mark`` no-ops and discovery with fixture injection from
conftest.py.  Real pytest, when installed, takes precedence.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import tempfile
import traceback
from pathlib import Path


class _RaisesContext:
    def __init__(self, expected):
        self.expected = expected
        self.value = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"DID NOT RAISE {self.expected!r}")
        if not issubclass(exc_type, self.expected):
            return False
        self.value = exc
        return True


class _Raises:
    def __call__(self, expected):
        return _RaisesContext(expected)


class _Approx:
    """Tiny stand-in for ``pytest.approx`` covering ``==`` comparisons."""

    def __init__(self, expected, rel=1e-6, abs=1e-12):
        self.expected = expected
        self.rel = rel
        self.abs = abs

    def __eq__(self, other):
        try:
            return abs(other - self.expected) <= max(
                self.rel * max(abs(other), abs(self.expected)), self.abs
            )
        except TypeError:
            return NotImplemented

    def __repr__(self):
        return f"approx({self.expected!r})"


def approx(expected, rel=1e-6, abs=1e-12):  # noqa: A001 - mirror pytest name
    """Approximate equality helper."""
    return _Approx(expected, rel, abs)


raises = _Raises()


class _Mark:
    def __getattr__(self, name):
        return lambda target=None, *a, **k: target if target is not None else (lambda f: f)

    def parametrize(self, argnames, argvalues):
        names = (
            [n.strip() for n in argnames.split(",") if n.strip()]
            if isinstance(argnames, str)
            else list(argnames)
        )

        def decorator(func):
            def wrapper(*outer_args, **outer_kwargs):
                for value in argvalues:
                    bound = dict(zip(names, value if isinstance(value, tuple) else (value,)))
                    bound.update(outer_kwargs)
                    func(*outer_args, **bound)

            wrapper.__name__ = getattr(func, "__name__", "case")
            wrapper.__wrapped__ = func
            return wrapper

        return decorator


mark = _Mark()


class _MonkeyPatch:
    """Tiny subset of pytest's ``monkeypatch``: ``setattr``/``delattr``."""

    def __init__(self):
        self._undo = []

    def setattr(self, target, name, value=None):
        if isinstance(target, str):
            module_name, _, attr = target.rpartition(".")
            target = importlib.import_module(module_name)
            name = attr
        had = hasattr(target, name)
        old = getattr(target, name, None)
        setattr(target, name, value)
        self._undo.append((target, name, had, old))

    def delattr(self, target, name=None):
        if isinstance(target, str):
            module_name, _, attr = target.rpartition(".")
            target = importlib.import_module(module_name)
            name = attr
        had = hasattr(target, name)
        old = getattr(target, name, None)
        if had:
            delattr(target, name)
        self._undo.append((target, name, had, old))

    def undo(self):
        for target, name, had, old in reversed(self._undo):
            if had:
                setattr(target, name, old)
            elif hasattr(target, name):
                delattr(target, name)
        self._undo.clear()


def fixture(func=None, **_kwargs):
    if func is None:
        return lambda f: f
    return func


def _instantiate(factory, fixtures, stack, cache):
    key = getattr(factory, "__module__", repr(factory)) + ":" + getattr(
        factory, "__name__", repr(factory)
    )
    if key in cache:
        return cache[key]
    if key in stack:
        raise RuntimeError(f"circular fixture: {key}")
    stack.add(key)
    sig = inspect.signature(factory if not inspect.isclass(factory) else factory.__init__)
    kwargs = {}
    for name in sig.parameters:
        if name == "self":
            continue
        if name in fixtures:
            kwargs[name] = _instantiate(fixtures[name], fixtures, stack, cache)
    stack.discard(key)
    if inspect.isclass(factory):
        value = factory(**kwargs)
    else:
        value = factory(**kwargs)
    cache[key] = value
    return value


def run(tests_dir: Path) -> int:
    sys.path.insert(0, str(tests_dir.parent))
    sys.path.insert(0, str(tests_dir))
    # Let test files and conftest.py ``import pytest`` without pytest installed.
    shim = importlib.import_module("_pytest_shim")
    sys.modules.setdefault("pytest", shim)

    def make_tmp_path():
        return Path(tempfile.mkdtemp(prefix="pyt-"))

    fixtures: dict[str, object] = {"monkeypatch": _MonkeyPatch}

    conftest = tests_dir / "conftest.py"
    if conftest.exists():
        conf = importlib.import_module("conftest")
        for name, value in vars(conf).items():
            if (
                inspect.isfunction(value)
                and getattr(value, "__module__", "") == conf.__name__
                and not name.startswith("_")
            ):
                fixtures[name] = value

    failures = 0
    passed = 0
    for path in sorted(tests_dir.glob("test_*.py")):
        module = importlib.import_module(path.stem)
        for name, func in sorted(vars(module).items()):
            if not (
                inspect.isfunction(func)
                and name.startswith("test_")
                and getattr(func, "__module__", "") == module.__name__
            ):
                continue
            try:
                # A fresh tmp_path per test, conftest fixtures cached within the
                # test so config/services/plant share one object graph.
                test_fixtures = dict(fixtures)
                test_fixtures["tmp_path"] = make_tmp_path
                cache: dict[str, object] = {}
                _instantiate(func, test_fixtures, set(), cache)
                passed += 1
                print(f". {path.stem}::{name}")
            except Exception:  # noqa: BLE001 - surface every failure
                failures += 1
                print(f"F {path.stem}::{name}")
                traceback.print_exc()
            finally:
                for value in cache.values():
                    undo = getattr(value, "undo", None)
                    if callable(undo):
                        undo()
    print(f"\n{passed} passed, {failures} failed")
    return 1 if failures else 0
