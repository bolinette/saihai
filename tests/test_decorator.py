from typing import Any

import pytest
from escondite import Cache
from peritype import FWrap

from saihai import CommandMeta, command, meta


def _registered(cache: Cache) -> list[FWrap[..., Any]]:
    return list(cache.get(CommandMeta.KEY, raises=False))


class TestDecoratorForm:
    def test_registers_the_function(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        assert [f.func for f in _registered(cache)] == [hello]

    def test_stores_path_and_summary(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        assert meta.get(hello, CommandMeta.KEY) == CommandMeta("hello", "Says hello", {})

    def test_returns_the_function_unchanged(self, cache: Cache) -> None:
        def hello() -> None:
            pass

        assert command("hello", "Says hello", cache=cache)(hello) is hello


class TestDirectForm:
    def test_registers_and_returns_the_function(self, cache: Cache) -> None:
        def hello() -> None:
            pass

        assert command(hello, "hello", "Says hello", cache=cache) is hello
        assert [f.func for f in _registered(cache)] == [hello]

    def test_stores_path_and_summary(self, cache: Cache) -> None:
        def hello() -> None:
            pass

        command(hello, "hello", "Says hello", cache=cache)

        assert meta.get(hello, CommandMeta.KEY) == CommandMeta("hello", "Says hello", {})


class TestExtras:
    def test_keyword_arguments_are_stored(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache, run_startup=False, group="core")
        def hello() -> None:
            pass

        assert meta.get(hello, CommandMeta.KEY).extras == {"run_startup": False, "group": "core"}

    def test_extras_default_to_an_empty_mapping(self, cache: Cache) -> None:
        assert CommandMeta("hello", "Says hello").extras == {}

    def test_cache_is_not_stored_as_an_extra(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        assert meta.get(hello, CommandMeta.KEY).extras == {}


class TestInvalidArguments:
    def test_missing_summary_raises(self, cache: Cache) -> None:
        with pytest.raises(TypeError):
            command("hello", cache=cache)  # pyright: ignore[reportCallIssue]

    def test_too_many_positional_arguments_raises(self, cache: Cache) -> None:
        def hello() -> None:
            pass

        with pytest.raises(TypeError):
            command(hello, "hello", "Says hello", "extra", cache=cache)  # pyright: ignore[reportCallIssue]


class TestCache:
    def test_commands_land_in_the_given_cache_only(self, cache: Cache) -> None:
        other = Cache()

        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        assert len(_registered(cache)) == 1
        assert _registered(other) == []

    def test_several_commands_accumulate(self, cache: Cache) -> None:
        @command("one", "First", cache=cache)
        def one() -> None:
            pass

        @command("two", "Second", cache=cache)
        def two() -> None:
            pass

        assert {f.func for f in _registered(cache)} == {one, two}
