import sys
from pathlib import Path
from typing import Annotated

import pytest
import typer
from typer.testing import CliRunner

runner = CliRunner()


def test_annotated_argument_with_default():
    app = typer.Typer()

    @app.command()
    def cmd(val: Annotated[int, typer.Argument()] = 0):
        print(f"hello {val}")

    result = runner.invoke(app)
    assert result.exit_code == 0, result.output
    assert "hello 0" in result.output

    result = runner.invoke(app, ["42"])
    assert result.exit_code == 0, result.output
    assert "hello 42" in result.output


def test_annotated_argument_in_string_type_with_default():
    app = typer.Typer()

    @app.command()
    def cmd(val: "Annotated[int, typer.Argument()]" = 0):
        print(f"hello {val}")

    result = runner.invoke(app)
    assert result.exit_code == 0, result.output
    assert "hello 0" in result.output

    result = runner.invoke(app, ["42"])
    assert result.exit_code == 0, result.output
    assert "hello 42" in result.output


def test_annotated_argument_with_default_factory():
    app = typer.Typer()

    def make_string():
        return "I made it"

    @app.command()
    def cmd(val: Annotated[str, typer.Argument(default_factory=make_string)]):
        print(val)

    result = runner.invoke(app)
    assert result.exit_code == 0, result.output
    assert "I made it" in result.output

    result = runner.invoke(app, ["overridden"])
    assert result.exit_code == 0, result.output
    assert "overridden" in result.output


def test_annotated_option_with_argname_doesnt_mutate_multiple_calls():
    app = typer.Typer()

    @app.command()
    def cmd(force: Annotated[bool, typer.Option("--force")] = False):
        if force:
            print("Forcing operation")
        else:
            print("Not forcing")

    result = runner.invoke(app)
    assert result.exit_code == 0, result.output
    assert "Not forcing" in result.output

    result = runner.invoke(app, ["--force"])
    assert result.exit_code == 0, result.output
    assert "Forcing operation" in result.output


def test_annotated_custom_path():
    app = typer.Typer()

    class CustomPath(Path):
        # Subclassing Path was not fully supported before 3.12
        # https://docs.python.org/3.12/whatsnew/3.12.html
        if sys.version_info < (3, 12):
            _flavour = type(Path())._flavour

    @app.command()
    def custom_parser(
        my_path: Annotated[CustomPath, typer.Argument(parser=CustomPath)],
    ):
        assert isinstance(my_path, CustomPath)

    result = runner.invoke(app, "/some/quirky/path/implementation")
    assert result.exit_code == 0


def test_annotated_option_invalid():
    app = typer.Typer()

    @app.command()
    def cmd(value: Annotated[str, typer.Option(..., "foo-bar")]):
        print(value)  # pragma: no cover

    with pytest.raises(ValueError, match="Invalid start character for option"):
        runner.invoke(app, ["--help"], catch_exceptions=False)


def test_annotated_pydantic_positive_int():
    from pydantic import PositiveInt

    app = typer.Typer()

    @app.command()
    def cmd(n: PositiveInt):
        print(f"n={n}")

    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "<int>" in help_result.output
    assert "Annotated" not in help_result.output

    ok = runner.invoke(app, ["5"])
    assert ok.exit_code == 0, ok.output
    assert "n=5" in ok.output

    bad = runner.invoke(app, ["--", "-5"])
    assert bad.exit_code == 2
    assert "Input should be greater than 0" in bad.output


def test_annotated_pydantic_field_with_option():
    from pydantic import Field

    app = typer.Typer()

    @app.command()
    def cmd(
        n: Annotated[int, Field(gt=0), typer.Option()],
        s: Annotated[str, Field(min_length=3), typer.Option()] = "abc",
    ):
        print(f"n={n}, s={s}")

    ok = runner.invoke(app, ["--n", "3", "--s", "hello"])
    assert ok.exit_code == 0, ok.output
    assert "n=3, s=hello" in ok.output

    bad_n = runner.invoke(app, ["--n", "0"])
    assert bad_n.exit_code == 2
    assert "Input should be greater than 0" in bad_n.output

    bad_s = runner.invoke(app, ["--n", "3", "--s", "ab"])
    assert bad_s.exit_code == 2
    assert "String should have at least 3 characters" in bad_s.output


def test_annotated_pydantic_after_validator_with_option():
    from pydantic import AfterValidator

    app = typer.Typer()

    @app.command()
    def cmd(s: Annotated[str, AfterValidator(str.upper), typer.Option()]):
        print(f"s={s}")

    result = runner.invoke(app, ["--s", "hello"])
    assert result.exit_code == 0, result.output
    assert "s=HELLO" in result.output


def test_annotated_pydantic_optional_and_collections():
    from pydantic import Field, PositiveInt

    app = typer.Typer()

    @app.command()
    def cmd(
        nums: Annotated[
            list[PositiveInt],
            Field(min_length=2),
            typer.Option(),
        ],
        opt: PositiveInt | None = None,
        pair: tuple[PositiveInt, str] = (1, "a"),
    ):
        print(f"opt={opt}, nums={nums}, pair={pair}")

    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0, help_result.output
    assert "Annotated" not in help_result.output

    ok = runner.invoke(
        app, ["--opt", "3", "--nums", "4", "--nums", "5", "--pair", "2", "b"]
    )
    assert ok.exit_code == 0, ok.output
    assert "opt=3, nums=[4, 5], pair=(2, 'b')" in ok.output

    bad_opt = runner.invoke(app, ["--nums", "1", "--nums", "2", "--opt", "-1"])
    assert bad_opt.exit_code == 2
    assert "Input should be greater than 0" in bad_opt.output

    bad_item = runner.invoke(app, ["--nums", "1", "--nums", "-2"])
    assert bad_item.exit_code == 2
    assert "Input should be greater than 0" in bad_item.output

    bad_len = runner.invoke(app, ["--nums", "1"])
    assert bad_len.exit_code == 2
    assert "List should have at least 2 items" in bad_len.output

    bad_pair = runner.invoke(app, ["--nums", "1", "--nums", "2", "--pair", "0", "b"])
    assert bad_pair.exit_code == 2
    assert "Input should be greater than 0" in bad_pair.output


def test_annotated_pydantic_validator_with_path(tmp_path: Path):
    from pydantic import AfterValidator

    def must_be_txt(p: Path) -> Path:
        if p.suffix != ".txt":
            raise ValueError("File must have .txt extension")
        return p

    txt_file = tmp_path / "ok.txt"
    txt_file.write_text("hi", encoding="utf-8")
    md_file = tmp_path / "bad.md"
    md_file.write_text("hi", encoding="utf-8")

    app = typer.Typer()

    @app.command()
    def cmd(
        file: Annotated[Path, AfterValidator(must_be_txt), typer.Option(exists=True)],
    ):
        print(f"file={file.name}")

    ok = runner.invoke(app, ["--file", str(txt_file)])
    assert ok.exit_code == 0, ok.output
    assert "file=ok.txt" in ok.output

    bad_ext = runner.invoke(app, ["--file", str(md_file)])
    assert bad_ext.exit_code == 2
    assert "File must have .txt extension" in bad_ext.output

    missing = runner.invoke(app, ["--file", str(tmp_path / "missing.txt")])
    assert missing.exit_code == 2
    assert "does not exist" in missing.output
