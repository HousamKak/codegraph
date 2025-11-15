"""Example Python code to demonstrate CodeGraph analysis."""


class Calculator:
    """A simple calculator class."""

    def __init__(self, precision: int = 2):
        """
        Initialize calculator.

        Args:
            precision: Number of decimal places for results
        """
        self.precision = precision

    def add(self, x: float, y: float) -> float:
        """
        Add two numbers.

        Args:
            x: First number
            y: Second number

        Returns:
            Sum of x and y
        """
        return round(x + y, self.precision)

    def subtract(self, x: float, y: float) -> float:
        """
        Subtract y from x.

        Args:
            x: First number
            y: Second number

        Returns:
            Difference of x and y
        """
        return round(x - y, self.precision)

    def multiply(self, x: float, y: float) -> float:
        """
        Multiply two numbers.

        Args:
            x: First number
            y: Second number

        Returns:
            Product of x and y
        """
        return round(x * y, self.precision)

    def divide(self, x: float, y: float) -> float:
        """
        Divide x by y.

        Args:
            x: Numerator
            y: Denominator

        Returns:
            Quotient of x and y

        Raises:
            ValueError: If y is zero
        """
        if y == 0:
            raise ValueError("Cannot divide by zero")
        return round(x / y, self.precision)


def calculate_total(items: list[float]) -> float:
    """
    Calculate total of all items.

    Args:
        items: List of numbers to sum

    Returns:
        Total sum
    """
    calc = Calculator()
    total = 0.0
    for item in items:
        total = calc.add(total, item)
    return total


def calculate_average(items: list[float]) -> float:
    """
    Calculate average of items.

    Args:
        items: List of numbers

    Returns:
        Average value

    Raises:
        ValueError: If items list is empty
    """
    if not items:
        raise ValueError("Cannot calculate average of empty list")

    total = calculate_total(items)
    calc = Calculator()
    return calc.divide(total, len(items))


def process_data(data: dict[str, list[float]]) -> dict[str, float]:
    """
    Process data dictionary and calculate averages.

    Args:
        data: Dictionary mapping names to lists of values

    Returns:
        Dictionary mapping names to averages
    """
    results = {}
    for name, values in data.items():
        if values:
            avg = calculate_average(values)
            results[name] = avg
    return results


# Example usage
if __name__ == "__main__":
    calc = Calculator(precision=3)

    # Test basic operations
    result1 = calc.add(10.5, 20.3)
    print(f"10.5 + 20.3 = {result1}")

    result2 = calc.multiply(5.0, 4.0)
    print(f"5.0 * 4.0 = {result2}")

    # Test higher-level functions
    numbers = [1.0, 2.0, 3.0, 4.0, 5.0]
    total = calculate_total(numbers)
    print(f"Total: {total}")

    average = calculate_average(numbers)
    print(f"Average: {average}")

    # Test data processing
    data = {
        "scores": [85.5, 90.0, 88.5],
        "temperatures": [20.1, 22.3, 21.8],
        "prices": [10.99, 15.49, 12.75]
    }

    results = process_data(data)
    for name, avg in results.items():
        print(f"{name} average: {avg}")
