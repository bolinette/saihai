# Saihai

Saihai turns a plain function into a command line command.
The decorator gives it a name and a summary, the type hints give it its arguments, and the parser turns `argv` into the call the host has to make.

Saihai parses, it never calls: `parse_command` hands back the function and the arguments it matched, and the host decides how to invoke it.
That is what lets an injection framework fill the parameters saihai knows nothing about.

Saihai is used by the [Bolinette project](https://github.com/bolinette) to build the `blnt` command line tool.

```python
from typing import Annotated

from escondite import Cache
from saihai import CommandArg, CommandOption, CommandParser, command

cache = Cache()


@command("greet", "Greets someone", cache=cache)
def greet(name: Annotated[str, CommandArg()], loud: Annotated[bool, CommandOption("l")] = False) -> None:
    print(f"HELLO {name.upper()}" if loud else f"Hello {name}")


cmd = CommandParser(cache, prog="mytool").parse_command(["greet", "Bob", "-l"])

assert cmd.args == {"name": "Bob", "loud": True}
cmd.func.func(**cmd.args)  # HELLO BOB
```

## Installation

```shell
$ pip install saihai  # or use your preferred package manager
```

## Requirements

Saihai requires Python 3.13 (or newer), and depends on [peritype](https://pypi.org/project/peritype/) to read the signatures it builds arguments from, on [hafersack](https://pypi.org/project/hafersack/) to tag the functions its decorator collects, and on [escondite](https://pypi.org/project/escondite/) for the cache that decorator writes to.

## Declaring a command

`command(path, summary)` registers a function, as a decorator or applied directly to one that already exists.
It returns the function untouched, so a command stays an ordinary function anyone can call.
Commands go into an escondite cache, the global one by default or the one given as `cache=`.

```python
from escondite import Cache
from saihai import command

cache = Cache()


@command("hello", "Says hello", cache=cache)
def hello() -> None:
    print("Hello")


def goodbye() -> None:
    print("Goodbye")


command(goodbye, "goodbye", "Says goodbye", cache=cache)
```

A path with spaces builds a tree of sub-commands, to any depth.
`db migrate` and `db seed` are two commands under the same `db` group, and `db` on its own asks for that group's help.

Any other keyword argument is kept verbatim in the command's `extras`, for the host to read back.
Saihai never interprets them, which is where a framework puts the flags that only mean something to it.

```python
from saihai import CommandMeta, meta


@command("db migrate", "Runs migrations", cache=cache, run_startup=True)
def migrate() -> None: ...


assert meta.get(migrate, CommandMeta.KEY).extras == {"run_startup": True}
```

## Declaring arguments

A parameter becomes an argument when it is annotated with `CommandArg()` for a positional one, or `CommandOption()` for a flag.
Both take a `summary=` shown in the help, and `CommandOption` takes a one-letter shorthand as its first argument.
An option is required unless it has a default or accepts `None`.

Parameters carrying neither marker are left alone and never reach the command line.
That is deliberate: it leaves room for the host to fill them with whatever it resolves services from.

```python
@command("serve", "Runs the server", cache=cache)
def serve(
    host: Annotated[str, CommandArg(summary="Address to bind")],
    logger: Logger,  # not a command line argument
    port: Annotated[int, CommandOption("p")] = 8080,
    verbose: Annotated[bool, CommandOption("v")] = False,
) -> None: ...
```

The type hint decides how the value is read, and a type saihai cannot map raises when the parser is built, not when the command runs.
A `list[T]` option is repeated one flag at a time, while a positional one takes every remaining value at once.

| Hint                  | Command line                                        |
| --------------------- | --------------------------------------------------- |
| `str`, `int`, `float` | Converted from the string form                      |
| `bytes`               | The argument is encoded                             |
| `bool`                | A flag, `--name`, defaulting to `False`             |
| `bool = True`         | An inverted flag: passing `--name` gives `False`    |
| `Literal["a", "b"]`   | A choice, rejected by the parser when it is not one |
| `Literal[1, 2]`       | The same, converted to `int`                        |
| `list[T]`             | A repeatable option, or a positional taking several  |
| `T \| None`           | Optional, `None` when absent                        |

## Parsing

`CommandParser(cache)` reads every command in the cache and builds the whole argparse tree once, and `prog=` and `description=` name the tool in the help text.
`parse_command(argv)` returns a `ParsedCommand` carrying the matched function, its `meta`, and the `args` the command line produced.

```python
@command("db rollback", "Rolls the last migration back", cache=cache)
def rollback(steps: Annotated[int, CommandOption("n")] = 1) -> None: ...


cmd = CommandParser(cache).parse_command(["db", "rollback", "-n", "3"])

assert cmd.meta.path == "db rollback"
assert cmd.meta.summary == "Rolls the last migration back"
assert cmd.args == {"steps": 3}
```

The parser never writes to the console and never exits the process.
Asking for help, or giving a command line it cannot accept, raises instead, and the error carries the text a command line tool would have printed.

## Reference

### Errors

All errors derive from `saihai.errors.SaihaiError`, and a `CommandError` carries the exit `code` a tool should end on.

| Error                    | Raised when                                                               |
| ------------------------ | ------------------------------------------------------------------------- |
| `CommandDefinitionError` | A command is malformed: a path conflict, or an argument saihai cannot map |
| `CommandHelpError`       | Help was asked for, or no command was given; code 0 or 1                  |
| `CommandUsageError`      | The command line does not match the command; code 2                       |

## License

Saihai is released under the MIT license, see [LICENSE.txt](LICENSE.txt).
