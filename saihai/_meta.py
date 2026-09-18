import inspect
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import Any, ClassVar

from hafersack import Hafersack
from peritype import FWrap, TWrap

from saihai.errors import CommandDefinitionError

meta = Hafersack("__saihai_meta__")


@dataclass(slots=True, frozen=True)
class CommandMeta:
    KEY: ClassVar[str] = "__saihai_cmd_meta__"

    path: str
    summary: str
    extras: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType[str, Any]({}))


class CommandParam:
    def __init__(self, *, default: Any | None = None, summary: str | None = None) -> None:
        self.default = default
        self.summary = summary


class CommandArg(CommandParam):
    pass


class CommandOption(CommandParam):
    def __init__(
        self,
        shorthand: str | None = None,
        /,
        *,
        default: Any | None = None,
        summary: str | None = None,
    ) -> None:
        CommandParam.__init__(self, default=default, summary=summary)
        self.shorthand = shorthand


class Command:
    def __init__(self, func: FWrap[..., Any], meta: CommandMeta) -> None:
        self._func = func
        self._meta = meta

    @property
    def func(self) -> FWrap[..., Any]:
        return self._func

    @property
    def meta(self) -> CommandMeta:
        return self._meta

    @cached_property
    def signature_hints(self) -> dict[str, TWrap[Any]]:
        return self._func.get_signature_hints()

    @cached_property
    def signature_parameters(self) -> dict[str, inspect.Parameter]:
        return {**self._func.signature.parameters}

    @cached_property
    def signature_cmd_params(self) -> dict[str, CommandParam]:
        params: dict[str, CommandParam] = {}
        for p_name, hint in self.signature_hints.items():
            for anno in hint.annotations:
                if isinstance(anno, type) and issubclass(anno, CommandParam):
                    raise CommandDefinitionError(
                        f"Command {self._func}, parameter '{p_name}', annotate with {anno.__name__}() "
                        "instead of the bare class"
                    )
                if isinstance(anno, CommandParam):
                    params[p_name] = anno
                    break
        return params


class ParsedCommand(Command):
    def __init__(self, origin: Command, args: dict[str, Any]) -> None:
        Command.__init__(self, origin.func, origin.meta)
        self._args = args

    @property
    def args(self) -> Mapping[str, Any]:
        return self._args
