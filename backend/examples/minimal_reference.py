"""Smallest possible script that still exercises every graph concept."""

from typing import Protocol


GLOBAL_CONFIG = {"version": "1.0"}


class Greeter(Protocol):
    """Simple protocol showing a type reference."""

    def greet(self, name: str) -> str:
        ...


class EchoGreeter:
    """Concrete class implementing the protocol."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def greet(self, name: str) -> str:
        return f"{self.prefix}{name}"


def format_message(greeter: Greeter, target: str) -> str:
    """Function referencing GLOBAL_CONFIG, classes, callsites, etc."""
    version = GLOBAL_CONFIG["version"]
    return f"[{version}] {greeter.greet(target)}"


def main() -> str:
    greeter = EchoGreeter(prefix="Hello, ")
    return format_message(greeter, "CodeGraph")


if __name__ == "__main__":
    print(main())
