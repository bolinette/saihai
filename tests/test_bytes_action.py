from argparse import ArgumentParser, Namespace

import pytest

from saihai import BytesArgparserAction


class TestBytesArgparserAction:
    def test_encodes_a_string_value(self) -> None:
        action = BytesArgparserAction[str](["--payload"], "payload")
        namespace = Namespace()

        action(ArgumentParser(), namespace, "hello")

        assert namespace.payload == b"hello"

    def test_encodes_every_value_of_a_sequence(self) -> None:
        action = BytesArgparserAction[str](["--payload"], "payload")
        namespace = Namespace()

        action(ArgumentParser(), namespace, ["hello", "world"])

        assert namespace.payload == [b"hello", b"world"]

    def test_rejects_non_string_values(self) -> None:
        action = BytesArgparserAction[str](["--payload"], "payload")

        with pytest.raises(TypeError):
            action(ArgumentParser(), Namespace(), [1, 2])

    def test_rejects_a_missing_value(self) -> None:
        action = BytesArgparserAction[str](["--payload"], "payload")

        with pytest.raises(TypeError):
            action(ArgumentParser(), Namespace(), None)
