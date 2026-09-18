from saihai import CommandArg, CommandOption, CommandParam


class TestCommandArg:
    def test_defaults(self) -> None:
        arg = CommandArg()

        assert arg.default is None
        assert arg.summary is None

    def test_carries_default_and_summary(self) -> None:
        arg = CommandArg(default="x", summary="Some value")

        assert arg.default == "x"
        assert arg.summary == "Some value"

    def test_is_a_command_param(self) -> None:
        assert isinstance(CommandArg(), CommandParam)


class TestCommandOption:
    def test_defaults(self) -> None:
        option = CommandOption()

        assert option.shorthand is None
        assert option.default is None
        assert option.summary is None

    def test_carries_a_shorthand(self) -> None:
        option = CommandOption("v", summary="Verbose")

        assert option.shorthand == "v"
        assert option.summary == "Verbose"

    def test_shorthand_is_positional_only(self) -> None:
        option = CommandOption("v", default=1)

        assert option.shorthand == "v"
        assert option.default == 1

    def test_is_a_command_param(self) -> None:
        assert isinstance(CommandOption(), CommandParam)
