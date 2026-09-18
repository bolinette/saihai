from collections.abc import Callable
from typing import Any, overload

from escondite import Cache
from peritype import wrap_func

from saihai._meta import CommandMeta, meta


def _set_meta(cache: Cache, func: Callable[..., Any], name: str, summary: str, extras: dict[str, Any]) -> None:
    meta.set(func, CommandMeta.KEY, CommandMeta(name, summary, extras))
    Cache.with_fallback(cache).add(CommandMeta.KEY, wrap_func(func))


@overload
def command[**P, T](
    func: Callable[P, T],
    name: str,
    summary: str,
    /,
    *,
    cache: Cache | None = None,
    **extras: Any,
) -> Callable[P, T]: ...
@overload
def command(
    name: str,
    summary: str,
    /,
    *,
    cache: Cache | None = None,
    **extras: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...
def command(*args: Any, cache: Cache | None = None, **extras: Any) -> Any:
    cache = Cache.with_fallback(cache)
    match args:
        case (str() as name, str() as summary):

            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                _set_meta(cache, func, name, summary, extras)
                return func

            return decorator
        case (func, str() as name, str() as summary):
            _set_meta(cache, func, name, summary, extras)
            return func
        case _:
            raise TypeError
