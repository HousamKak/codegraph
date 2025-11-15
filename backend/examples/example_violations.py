"""Example code with conservation law violations for testing."""


class DataProcessor:
    """Example class with some violations."""

    def process(self, data: str) -> int:
        """
        Process data.

        Args:
            data: Input data

        Returns:
            Processed result
        """
        # VIOLATION: Return type mismatch - returns string instead of int
        return "processed: " + data

    def _private_helper(self, value: int) -> int:
        """
        Private helper function.

        Args:
            value: Input value

        Returns:
            Processed value
        """
        return value * 2


def calculate(x, y):  # VIOLATION: Missing type annotations
    """
    Calculate something.

    Args:
        x: First value
        y: Second value

    Returns:
        Result
    """
    return x + y


def call_examples():
    """Function demonstrating various call patterns."""
    processor = DataProcessor()

    # Correct call
    result1 = processor.process("hello")

    # VIOLATION: Incorrect number of arguments
    result2 = calculate(1, 2, 3)

    # VIOLATION: Calling undefined function
    result3 = undefined_function(42)

    # VIOLATION: Accessing private method from outside
    result4 = processor._private_helper(10)

    return result1


def function_with_params(a: int, b: str, c: float = 3.14) -> str:
    """
    Function with multiple parameters.

    Args:
        a: Integer parameter
        b: String parameter
        c: Float parameter with default

    Returns:
        Combined result
    """
    result = calculate(a, c)  # Correct call
    return f"{b}: {result}"


# Missing type annotation on return
def get_value():
    """Get a value."""
    return 42


# Circular dependency example (if we had another file)
class A:
    """Class A."""

    def method_a(self):
        """Method A."""
        # This would create circular call if B.method_b calls back to A.method_a
        b = B()
        return b.method_b()


class B:
    """Class B."""

    def method_b(self):
        """Method B."""
        a = A()
        return a.method_a()  # Creates circular dependency


if __name__ == "__main__":
    # VIOLATION: Wrong number of arguments
    result = function_with_params(1, "test", 2.5, "extra")
    print(result)
