import inspect
from argparse import Action, ArgumentParser, Namespace
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Protocol, cast, override

from escondite import Cache
from peritype import FWrap, TWrap, wrap_type

from saihai._meta import Command, CommandMeta, CommandOption, CommandParam, ParsedCommand, meta
from saihai.errors import CommandDefinitionError, CommandHelpError, CommandUsageError

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

VALUELESS_ACTIONS = frozenset({"store_true", "store_false", "store_const"})

COMMAND_DEST = "__saihai_cmd__"
PATH_DEST = "__saihai_path__"


class _SubParsersAction(Protocol):
    def add_parser(self, name: str, *, help: str | None = None) -> ArgumentParser: ...


class _ArgumentParser(ArgumentParser):
    _help: str | None = None

    @override
    def print_help(self, file: "SupportsWrite[str] | None" = None) -> None:
        self._help = self.format_help()

    @override
    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if status == 0:
            raise CommandHelpError(self._help or message or "", code=0)
        raise CommandUsageError(message or "", code=status)

    @override
    def error(self, message: str) -> NoReturn:
        self.exit(2, f"{self.format_usage()}{self.prog}: error: {message}")


class CommandParser:
    def __init__(self, cache: Cache, *, prog: str | None = None, description: str | None = None) -> None:
        self._cache = cache
        self._commands: dict[str, Command] = {}
        self._sub_commands: dict[str, ArgumentParser] = {}
        self._parser = _ArgumentParser(prog=prog, description=description)
        self._parse_commands()

    def _parse_commands(self) -> None:
        functions = self._cache.get(CommandMeta.KEY, hint=FWrap[..., Any], raises=False)
        commands: dict[str, Command] = {}
        command_tree: dict[str, Any] = {}
        for func in functions:
            _cmd = meta.get(func.func, CommandMeta.KEY)
            cur_node = command_tree
            path = _cmd.path.split(" ")
            for elem in path[:-1]:
                if elem not in cur_node:
                    cur_node[elem] = {}
                cur_node = cur_node[elem]
            elem = path[-1]
            if elem in cur_node:
                raise CommandDefinitionError(f"Conflict with '{_cmd.path}' command")
            command = Command(func, _cmd)
            cur_node[elem] = command
            commands[_cmd.path] = command
        self._commands = commands
        self._build_parsers(command_tree, self._parser.add_subparsers(), [])

    def _build_parsers(
        self,
        command_tree: dict[str, dict[str, Any] | Command],
        sub_parsers: _SubParsersAction,
        path: list[str],
    ) -> None:
        for name, elem in command_tree.items():
            if isinstance(elem, Command):
                sub_parser = sub_parsers.add_parser(name, help=elem.meta.summary)
                hints = elem.signature_hints
                cmd_params = elem.signature_cmd_params
                for p_name, param in elem.signature_parameters.items():
                    if p_name not in hints or p_name not in cmd_params:
                        continue
                    flags, kwargs = self._create_argument(elem.func, p_name, param, hints[p_name], cmd_params[p_name])
                    sub_parser.add_argument(*flags, **kwargs)
                sub_parser.set_defaults(**{COMMAND_DEST: elem.meta.path})
            else:
                sub_path = [*path, name]
                group = " ".join(sub_path)
                sub_parser = sub_parsers.add_parser(name, help=self._build_help(elem, sub_path))
                sub_parser.set_defaults(**{PATH_DEST: group})
                self._sub_commands[group] = sub_parser
                self._build_parsers(elem, sub_parser.add_subparsers(), sub_path)

    @staticmethod
    def _create_argument(
        func: FWrap[..., Any],
        p_name: str,
        param: inspect.Parameter,
        type: TWrap[Any],
        cmd_param: CommandParam,
    ) -> tuple[list[str], dict[str, Any]]:
        flags, kwargs = CommandParser._build_argument(func, p_name, param, type, cmd_param)
        action = kwargs.get("action")
        takes_a_value = action not in VALUELESS_ACTIONS
        if isinstance(cmd_param, CommandOption):
            if takes_a_value and not type.nullable and "default" not in kwargs:
                kwargs["required"] = True
        elif takes_a_value and "nargs" not in kwargs and "default" in kwargs:
            kwargs["nargs"] = "?"
        if cmd_param.summary:
            kwargs["help"] = cmd_param.summary
        return flags, kwargs

    @staticmethod
    def _build_argument(
        func: FWrap[..., Any],
        p_name: str,
        param: inspect.Parameter,
        type: TWrap[Any],
        cmd_param: CommandParam,
    ) -> tuple[list[str], dict[str, Any]]:
        flags: list[str]
        kwargs: dict[str, Any] = {}
        if param.default != inspect.Signature.empty:
            kwargs["default"] = param.default
        if isinstance(cmd_param, CommandOption):
            flags = [f"--{p_name}"]
            if cmd_param.shorthand:
                flags.append(f"-{cmd_param.shorthand}")
        else:
            flags = [p_name]
            if type.nullable:
                raise CommandDefinitionError(
                    f"Command {func}, parameter '{p_name}', a positional argument cannot be nullable"
                )
        if type.match(str):
            kwargs["type"] = str
        elif type.match(int):
            kwargs["type"] = int
        elif type.match(float):
            kwargs["type"] = float
        elif type.match(bytes):
            kwargs["action"] = BytesArgparserAction
        elif type.match(bool):
            if "default" in kwargs:
                if kwargs["default"] is False:
                    kwargs["action"] = "store_true"
                else:
                    kwargs["action"] = "store_false"
                del kwargs["default"]
            else:
                kwargs["action"] = "store_true"
        elif type.nodes[0].inner_type is Literal:
            literal_params = type.nodes[0].origin_params
            if len(literal_params) == 1:
                if literal_params == (True,):
                    kwargs["action"] = "store_true"
                elif literal_params == (False,):
                    kwargs["action"] = "store_false"
                else:
                    kwargs["action"] = "store_const"
                    kwargs["const"] = literal_params[0]
            else:
                if all(isinstance(i, str) for i in literal_params):
                    kwargs["action"] = "store"
                    kwargs["type"] = str
                elif all(isinstance(i, int) for i in literal_params):
                    kwargs["action"] = "store"
                    kwargs["type"] = int
                else:
                    raise CommandDefinitionError(
                        f"Command {func}, parameter '{p_name}', {type} is not a valid argument type"
                    )
                kwargs["choices"] = literal_params
        elif type.match(list[Any]):
            flags, kwargs = CommandParser._build_argument(
                func, p_name, param, wrap_type(type.generic_params[0]), cmd_param
            )
            if kwargs.get("action") in VALUELESS_ACTIONS:
                raise CommandDefinitionError(
                    f"Command {func}, parameter '{p_name}', type {type} is not allowed as a command argument"
                )
            if isinstance(cmd_param, CommandOption):
                kwargs["action"] = "append"
            else:
                kwargs["nargs"] = "*" if "default" in kwargs else "+"
        else:
            raise CommandDefinitionError(
                f"Command {func}, parameter '{p_name}', type {type} is not allowed as a command argument"
            )
        return flags, kwargs

    def parse_command(self, args: Sequence[str]) -> ParsedCommand:
        parsed = vars(self._parser.parse_args([*args]))
        if COMMAND_DEST in parsed:
            cmd = parsed.pop(COMMAND_DEST)
            parsed.pop(PATH_DEST, None)
            return ParsedCommand(self._commands[cmd], parsed)
        if PATH_DEST in parsed:
            raise CommandHelpError(self._sub_commands[parsed[PATH_DEST]].format_help())
        raise CommandHelpError(self._parser.format_help())

    @staticmethod
    def _build_help(command_tree: dict[str, Any], path: list[str]) -> str:
        commands = [f'"{" ".join([*path, x])}"' for x in command_tree]
        return "Sub-commands: " + ", ".join(commands)


class BytesArgparserAction[T](Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        nargs: int | str | None = None,
        const: T | None = None,
        default: T | str | None = None,
        type: Callable[[str], T] | None = None,
        choices: Iterable[T] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)

    @override
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        if isinstance(values, str):
            setattr(namespace, self.dest, values.encode())
            return
        if isinstance(values, Sequence) and all(isinstance(value, str) for value in values):
            setattr(namespace, self.dest, [cast(str, value).encode() for value in values])
            return
        raise TypeError
