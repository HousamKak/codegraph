"""Example with highly connected functions to demonstrate graph connectivity."""


def load_data(filename: str) -> list:
    """Load data from file."""
    return parse_file(filename)


def parse_file(filename: str) -> list:
    """Parse file content."""
    content = read_file(filename)
    return process_content(content)


def read_file(filename: str) -> str:
    """Read file."""
    with open(filename) as f:
        return f.read()


def process_content(content: str) -> list:
    """Process content."""
    lines = split_lines(content)
    return filter_lines(lines)


def split_lines(content: str) -> list:
    """Split content into lines."""
    return content.split('\n')


def filter_lines(lines: list) -> list:
    """Filter empty lines."""
    return [line for line in lines if line.strip()]


def calculate_total(items: list, apply_discount: bool) -> float:
    """Calculate total with required discount flag."""
    validated = validate_items(items)
    total = sum_items(validated)
    if apply_discount:
        total = total * 0.9
    return total


def validate_items(items: list) -> list:
    """Validate items."""
    return [x for x in items if check_valid(x)]


def check_valid(item) -> bool:
    """Check if item is valid."""
    return item is not None and item > 0


def sum_items(items: list) -> float:
    """Sum all items."""
    return sum(items)


def main():
    """Main function that orchestrates everything."""
    # This creates a connected graph!
    data = load_data("data.txt")
    total = calculate_total(data)
    result = format_result(total)
    save_result(result)
    return result


def format_result(total: float) -> str:
    """Format the result."""
    return f"Total: {total}"


def save_result(result: str):
    """Save result to file."""
    write_file("output.txt", result)


def write_file(filename: str, content: str):
    """Write content to file."""
    with open(filename, 'w') as f:
        f.write(content)


if __name__ == "__main__":
    main()
