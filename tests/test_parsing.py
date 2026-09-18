from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal

import pytest
from escondite import Cache

from saihai import CommandArg, CommandOption, CommandParser, command
from saihai.errors import CommandDefinitionError, CommandHelpError, CommandUsageError


def _parse(cache: Cache, args: Sequence[str]) -> Mapping[str, Any]:
    return CommandParser(cache).parse_command(args).args


class TestPositionalArguments:
    def test_string(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandArg()]) -> None:
            pass

        assert _parse(cache, ["greet", "Bob"]) == {"name": "Bob"}

    def test_int_and_float_are_converted(self, cache: Cache) -> None:
        @command("calc", "Computes", cache=cache)
        def calc(count: Annotated[int, CommandArg()], ratio: Annotated[float, CommandArg()]) -> None:
            pass

        assert _parse(cache, ["calc", "3", "1.5"]) == {"count": 3, "ratio": 1.5}

    def test_bytes_are_encoded(self, cache: Cache) -> None:
        @command("send", "Sends", cache=cache)
        def send(payload: Annotated[bytes, CommandArg()]) -> None:
            pass

        assert _parse(cache, ["send", "hello"]) == {"payload": b"hello"}

    def test_default_is_used_when_absent(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandArg()] = "World") -> None:
            pass

        assert _parse(cache, ["greet"]) == {"name": "World"}

    def test_missing_required_argument_is_a_usage_error(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandArg()]) -> None:
            pass

        with pytest.raises(CommandUsageError) as info:
            _parse(cache, ["greet"])

        assert info.value.code == 2

    def test_wrong_type_is_a_usage_error(self, cache: Cache) -> None:
        @command("calc", "Computes", cache=cache)
        def calc(count: Annotated[int, CommandArg()]) -> None:
            pass

        with pytest.raises(CommandUsageError):
            _parse(cache, ["calc", "nope"])

    def test_nullable_positional_is_rejected(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str | None, CommandArg()]) -> None:
            pass

        with pytest.raises(CommandDefinitionError, match="cannot be nullable"):
            CommandParser(cache)


class TestOptions:
    def test_long_flag(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandOption()]) -> None:
            pass

        assert _parse(cache, ["greet", "--name", "Bob"]) == {"name": "Bob"}

    def test_shorthand_flag(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandOption("n")]) -> None:
            pass

        assert _parse(cache, ["greet", "-n", "Bob"]) == {"name": "Bob"}

    def test_option_without_default_is_required(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandOption()]) -> None:
            pass

        with pytest.raises(CommandUsageError):
            _parse(cache, ["greet"])

    def test_option_with_default_is_optional(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandOption()] = "World") -> None:
            pass

        assert _parse(cache, ["greet"]) == {"name": "World"}

    def test_nullable_option_is_optional(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str | None, CommandOption()]) -> None:
            pass

        assert _parse(cache, ["greet"]) == {"name": None}

    def test_nullable_option_takes_a_value(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str | None, CommandOption()]) -> None:
            pass

        assert _parse(cache, ["greet", "--name", "Bob"]) == {"name": "Bob"}


class TestBooleanFlags:
    def test_bare_bool_is_a_flag(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(loud: Annotated[bool, CommandOption()]) -> None:
            pass

        assert _parse(cache, ["greet"]) == {"loud": False}
        assert _parse(cache, ["greet", "--loud"]) == {"loud": True}

    def test_bool_defaulting_to_false_stores_true(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(loud: Annotated[bool, CommandOption()] = False) -> None:
            pass

        assert _parse(cache, ["greet"]) == {"loud": False}
        assert _parse(cache, ["greet", "--loud"]) == {"loud": True}

    def test_bool_defaulting_to_true_stores_false(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(quiet: Annotated[bool, CommandOption()] = True) -> None:
            pass

        assert _parse(cache, ["greet"]) == {"quiet": True}
        assert _parse(cache, ["greet", "--quiet"]) == {"quiet": False}


class TestLiterals:
    def test_several_string_choices(self, cache: Cache) -> None:
        @command("log", "Logs", cache=cache)
        def log(level: Annotated[Literal["debug", "info"], CommandOption()]) -> None:
            pass

        assert _parse(cache, ["log", "--level", "info"]) == {"level": "info"}

    def test_value_outside_the_choices_is_a_usage_error(self, cache: Cache) -> None:
        @command("log", "Logs", cache=cache)
        def log(level: Annotated[Literal["debug", "info"], CommandOption()]) -> None:
            pass

        with pytest.raises(CommandUsageError):
            _parse(cache, ["log", "--level", "trace"])

    def test_several_int_choices(self, cache: Cache) -> None:
        @command("key", "Makes a key", cache=cache)
        def key(size: Annotated[Literal[2048, 4096], CommandOption()]) -> None:
            pass

        assert _parse(cache, ["key", "--size", "4096"]) == {"size": 4096}

    def test_single_true_literal_is_a_flag(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(loud: Annotated[Literal[True], CommandOption()]) -> None:
            pass

        assert _parse(cache, ["greet"]) == {"loud": False}
        assert _parse(cache, ["greet", "--loud"]) == {"loud": True}

    def test_single_false_literal_is_an_inverted_flag(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(quiet: Annotated[Literal[False], CommandOption()]) -> None:
            pass

        assert _parse(cache, ["greet"]) == {"quiet": True}
        assert _parse(cache, ["greet", "--quiet"]) == {"quiet": False}

    def test_nullable_single_true_literal_is_a_flag(self, cache: Cache) -> None:
        @command("run", "Runs", cache=cache)
        def run(force: Annotated[Literal[True] | None, CommandOption()]) -> None:
            pass

        assert _parse(cache, ["run"]) == {"force": False}
        assert _parse(cache, ["run", "--force"]) == {"force": True}

    def test_nullable_single_false_literal_is_an_inverted_flag(self, cache: Cache) -> None:
        @command("run", "Runs", cache=cache)
        def run(color: Annotated[Literal[False] | None, CommandOption()]) -> None:
            pass

        assert _parse(cache, ["run"]) == {"color": True}
        assert _parse(cache, ["run", "--color"]) == {"color": False}

    def test_single_other_literal_stores_a_constant(self, cache: Cache) -> None:
        @command("log", "Logs", cache=cache)
        def log(level: Annotated[Literal["debug"], CommandOption()]) -> None:
            pass

        assert _parse(cache, ["log", "--level"]) == {"level": "debug"}

    def test_mixed_literal_types_are_rejected(self, cache: Cache) -> None:
        @command("log", "Logs", cache=cache)
        def log(level: Annotated[Literal["debug", 1], CommandOption()]) -> None:
            pass

        with pytest.raises(CommandDefinitionError, match="not a valid argument type"):
            CommandParser(cache)


class TestLists:
    def test_repeated_option_appends(self, cache: Cache) -> None:
        @command("tag", "Tags", cache=cache)
        def tag(name: Annotated[list[str], CommandOption()]) -> None:
            pass

        assert _parse(cache, ["tag", "--name", "a", "--name", "b"]) == {"name": ["a", "b"]}

    def test_element_type_is_converted(self, cache: Cache) -> None:
        @command("pick", "Picks", cache=cache)
        def pick(number: Annotated[list[int], CommandOption()]) -> None:
            pass

        assert _parse(cache, ["pick", "--number", "1", "--number", "2"]) == {"number": [1, 2]}

    def test_required_when_not_nullable(self, cache: Cache) -> None:
        @command("tag", "Tags", cache=cache)
        def tag(name: Annotated[list[str], CommandOption()]) -> None:
            pass

        with pytest.raises(CommandUsageError):
            _parse(cache, ["tag"])

    def test_positional_list_collects_every_value(self, cache: Cache) -> None:
        @command("tag", "Tags", cache=cache)
        def tag(names: Annotated[list[str], CommandArg()]) -> None:
            pass

        assert _parse(cache, ["tag", "a", "b", "c"]) == {"names": ["a", "b", "c"]}

    def test_positional_list_without_a_default_needs_one_value(self, cache: Cache) -> None:
        @command("tag", "Tags", cache=cache)
        def tag(names: Annotated[list[str], CommandArg()]) -> None:
            pass

        with pytest.raises(CommandUsageError):
            _parse(cache, ["tag"])

    def test_positional_list_element_type_is_converted(self, cache: Cache) -> None:
        @command("pick", "Picks", cache=cache)
        def pick(numbers: Annotated[list[int], CommandArg()]) -> None:
            pass

        assert _parse(cache, ["pick", "1", "2"]) == {"numbers": [1, 2]}

    def test_positional_list_of_bytes_encodes_every_value(self, cache: Cache) -> None:
        @command("send", "Sends", cache=cache)
        def send(blobs: Annotated[list[bytes], CommandArg()]) -> None:
            pass

        assert _parse(cache, ["send", "a", "b"]) == {"blobs": [b"a", b"b"]}

    def test_positional_list_is_followed_by_options(self, cache: Cache) -> None:
        @command("tag", "Tags", cache=cache)
        def tag(names: Annotated[list[str], CommandArg()], loud: Annotated[bool, CommandOption("l")] = False) -> None:
            pass

        assert _parse(cache, ["tag", "a", "b", "-l"]) == {"names": ["a", "b"], "loud": True}

    def test_list_of_a_valueless_type_is_rejected(self, cache: Cache) -> None:
        @command("tag", "Tags", cache=cache)
        def tag(flags: Annotated[list[bool], CommandArg()]) -> None:
            pass

        with pytest.raises(CommandDefinitionError, match="not allowed as a command argument"):
            CommandParser(cache)

    def test_positional_list_with_a_default_is_optional(self, cache: Cache) -> None:
        empty: list[str] = []

        @command("tag", "Tags", cache=cache)
        def tag(names: Annotated[list[str], CommandArg()] = empty) -> None:
            pass

        assert _parse(cache, ["tag"]) == {"names": []}

    def test_nullable_list_is_optional(self, cache: Cache) -> None:
        @command("tag", "Tags", cache=cache)
        def tag(name: Annotated[list[str] | None, CommandOption()]) -> None:
            pass

        assert _parse(cache, ["tag"]) == {"name": None}


class TestUnsupportedTypes:
    def test_unknown_type_is_rejected(self, cache: Cache) -> None:
        @command("run", "Runs", cache=cache)
        def run(value: Annotated[complex, CommandArg()]) -> None:
            pass

        with pytest.raises(CommandDefinitionError, match="not allowed as a command argument"):
            CommandParser(cache)

    def test_bare_arg_class_is_rejected(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandArg]) -> None:
            pass

        with pytest.raises(CommandDefinitionError, match=r"CommandArg\(\) instead of the bare class"):
            CommandParser(cache)

    def test_bare_option_class_is_rejected(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(loud: Annotated[bool, CommandOption] = False) -> None:
            pass

        with pytest.raises(CommandDefinitionError, match=r"CommandOption\(\) instead of the bare class"):
            CommandParser(cache)

    def test_foreign_annotations_are_ignored(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(service: Annotated[object, "not a command param"], name: Annotated[str, CommandArg()]) -> None:
            pass

        assert _parse(cache, ["greet", "Bob"]) == {"name": "Bob"}

    def test_unannotated_parameters_are_ignored(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(service: object, name: Annotated[str, CommandArg()]) -> None:
            pass

        assert _parse(cache, ["greet", "Bob"]) == {"name": "Bob"}


class TestCommandTree:
    def test_flat_command(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        assert CommandParser(cache).parse_command(["hello"]).func.func is hello

    def test_nested_commands_share_a_group(self, cache: Cache) -> None:
        @command("db migrate", "Migrates", cache=cache)
        def migrate() -> None:
            pass

        @command("db seed", "Seeds", cache=cache)
        def seed() -> None:
            pass

        parser = CommandParser(cache)

        assert parser.parse_command(["db", "migrate"]).func.func is migrate
        assert parser.parse_command(["db", "seed"]).func.func is seed

    def test_parsed_command_keeps_its_meta(self, cache: Cache) -> None:
        @command("db migrate", "Migrates", cache=cache, run_startup=False)
        def migrate() -> None:
            pass

        parsed = CommandParser(cache).parse_command(["db", "migrate"])

        assert parsed.meta.path == "db migrate"
        assert parsed.meta.summary == "Migrates"
        assert parsed.meta.extras == {"run_startup": False}

    def test_internal_dests_are_not_in_the_arguments(self, cache: Cache) -> None:
        @command("db migrate", "Migrates", cache=cache)
        def migrate(name: Annotated[str, CommandArg()]) -> None:
            pass

        assert CommandParser(cache).parse_command(["db", "migrate", "x"]).args == {"name": "x"}

    def test_conflicting_paths_are_rejected(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def one() -> None:
            pass

        @command("hello", "Says hello again", cache=cache)
        def two() -> None:
            pass

        with pytest.raises(CommandDefinitionError, match="Conflict with 'hello' command"):
            CommandParser(cache)

    def test_unknown_command_is_a_usage_error(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        with pytest.raises(CommandUsageError):
            _parse(cache, ["nope"])


class TestHelp:
    def test_no_arguments_shows_the_root_help(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, [])

        assert info.value.code == 1
        assert "hello" in info.value.message

    def test_group_without_a_sub_command_shows_the_group_help(self, cache: Cache) -> None:
        @command("db migrate", "Migrates", cache=cache)
        def migrate() -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, ["db"])

        assert "migrate" in info.value.message

    def test_group_help_lists_the_full_sub_command_paths(self, cache: Cache) -> None:
        @command("db migrate", "Migrates", cache=cache)
        def migrate() -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, [])

        assert '"db migrate"' in info.value.message

    def test_explicit_help_flag_exits_with_zero(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, ["--help"])

        assert info.value.code == 0

    def test_command_summary_appears_in_the_help(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, [])

        assert "Says hello" in info.value.message

    def test_parameter_summary_appears_in_the_command_help(self, cache: Cache) -> None:
        @command("greet", "Greets", cache=cache)
        def greet(name: Annotated[str, CommandArg(summary="Who to greet")]) -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, ["greet", "--help"])

        assert "Who to greet" in info.value.message

    def test_prog_and_description_are_used(self, cache: Cache) -> None:
        @command("hello", "Says hello", cache=cache)
        def hello() -> None:
            pass

        parser = CommandParser(cache, prog="mytool", description="My tool")

        with pytest.raises(CommandHelpError) as info:
            parser.parse_command([])

        assert "mytool" in info.value.message
        assert "My tool" in info.value.message

    def test_deep_group_without_a_sub_command_shows_its_help(self, cache: Cache) -> None:
        @command("db schema migrate", "Migrates", cache=cache)
        def migrate() -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, ["db", "schema"])

        assert "migrate" in info.value.message

    def test_two_groups_with_the_same_leaf_name_keep_their_own_help(self, cache: Cache) -> None:
        @command("auth new rsa", "Creates an RSA key", cache=cache)
        def rsa() -> None:
            pass

        @command("new project", "Creates a project", cache=cache)
        def project() -> None:
            pass

        with pytest.raises(CommandHelpError) as info:
            _parse(cache, ["auth", "new"])

        assert "rsa" in info.value.message


class TestEmptyCache:
    def test_a_parser_without_commands_shows_its_help(self, cache: Cache) -> None:
        with pytest.raises(CommandHelpError):
            _parse(cache, [])
