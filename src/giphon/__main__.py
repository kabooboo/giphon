#!/usr/bin/python3

from typer import Typer

from .siphon import siphon

# TODO: add CI


if __name__ == "__main__":

    app = Typer(no_args_is_help=True, add_completion=False)

    app.command()(siphon)
    app()
