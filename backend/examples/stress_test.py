"""
Comprehensive stress test for CodeGraph - Real Python patterns only.

This file tests CodeGraph's ability to handle:
1. Multiple inheritance (Diamond problem)
2. Method overriding
3. Decorators (property, staticmethod, classmethod, custom)
4. Abstract base classes
5. Generators and async functions
6. Recursive functions (including mutual recursion)
7. Nested functions and closures
8. Higher-order functions
9. Lambda functions
10. Type hints with generics
11. Context managers
12. Complex call chains
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Callable, Optional
from functools import wraps
import asyncio


# ============================================================================
# 1. ABSTRACT BASE CLASSES
# ============================================================================

class Animal(ABC):
    """Abstract base class."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def make_sound(self) -> str:
        """Must be implemented by subclasses."""
        pass

    def describe(self) -> str:
        """Concrete method in abstract class."""
        return f"{self.name} says {self.make_sound()}"


# ============================================================================
# 2. MULTIPLE INHERITANCE (Diamond Problem)
# ============================================================================

class Flyer:
    """Mixin for flying animals."""

    def fly(self) -> str:
        return f"{self.name} is flying"


class Swimmer:
    """Mixin for swimming animals."""

    def swim(self) -> str:
        return f"{self.name} is swimming"


class Duck(Flyer, Swimmer, Animal):
    """Duck has multiple inheritance - can fly and swim."""

    def make_sound(self) -> str:
        return "Quack!"

    def do_everything(self) -> str:
        """Calls methods from all parent classes."""
        sound = self.describe()  # From Animal
        flying = self.fly()      # From Flyer
        swimming = self.swim()   # From Swimmer
        return f"{sound}, {flying}, {swimming}"


class Dog(Animal):
    """Simple single inheritance."""

    def make_sound(self) -> str:
        return "Woof!"


# ============================================================================
# 3. DECORATORS
# ============================================================================

def log_calls(func: Callable) -> Callable:
    """Custom decorator that logs function calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"Called {func.__name__} with result: {result}")
        return result
    return wrapper


class Calculator:
    """Demonstrates property, staticmethod, classmethod."""

    _instance_count = 0

    def __init__(self, name: str):
        self._name = name
        self._value = 0
        Calculator._instance_count += 1

    @property
    def value(self) -> int:
        """Property getter."""
        return self._value

    @value.setter
    def value(self, val: int):
        """Property setter."""
        self._value = val

    @staticmethod
    def create_default() -> 'Calculator':
        """Static method - no self."""
        return Calculator("default")

    @classmethod
    def get_count(cls) -> int:
        """Class method - gets cls."""
        return cls._instance_count

    @log_calls
    def add(self, x: int, y: int) -> int:
        """Method with custom decorator."""
        result = x + y
        self.value = result
        return result


# ============================================================================
# 4. GENERICS
# ============================================================================

T = TypeVar('T')


class Stack(Generic[T]):
    """Generic stack implementation."""

    def __init__(self):
        self._items: List[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> Optional[T]:
        if self._items:
            return self._items.pop()
        return None

    def transform(self, func: Callable[[T], T]) -> 'Stack[T]':
        """Higher-order method with generics."""
        new_stack = Stack[T]()
        new_stack._items = [func(item) for item in self._items]
        return new_stack


# ============================================================================
# 5. NESTED FUNCTIONS & CLOSURES
# ============================================================================

def make_multiplier(factor: int) -> Callable[[int], int]:
    """Returns a closure."""

    def multiply(x: int) -> int:
        """Nested function - closes over factor."""
        return x * factor

    return multiply


def deeply_nested(a: int) -> int:
    """Three levels of nesting."""

    def level1(b: int) -> int:
        def level2(c: int) -> int:
            def level3(d: int) -> int:
                return a + b + c + d
            return level3(4)
        return level2(3)
    return level1(2)


# ============================================================================
# 6. RECURSIVE FUNCTIONS
# ============================================================================

def factorial(n: int) -> int:
    """Classic recursion."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n: int) -> int:
    """Fibonacci recursion."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


# Mutual recursion
def is_even(n: int) -> bool:
    """Mutual recursion - calls is_odd."""
    if n == 0:
        return True
    return is_odd(n - 1)


def is_odd(n: int) -> bool:
    """Mutual recursion - calls is_even."""
    if n == 0:
        return False
    return is_even(n - 1)


# ============================================================================
# 7. GENERATORS
# ============================================================================

def count_up_to(n: int):
    """Simple generator."""
    for i in range(n):
        yield i


def fibonacci_gen():
    """Infinite generator."""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def generator_pipeline(data: List[int]):
    """Generator that calls another generator."""
    for item in count_up_to(len(data)):
        yield data[item] * 2


# ============================================================================
# 8. ASYNC FUNCTIONS
# ============================================================================

async def fetch_data(url: str) -> str:
    """Async function."""
    await asyncio.sleep(0.01)
    return f"Data from {url}"


async def fetch_multiple(urls: List[str]) -> List[str]:
    """Async function calling async function."""
    results = []
    for url in urls:
        data = await fetch_data(url)
        results.append(data)
    return results


async def process_async(urls: List[str]) -> str:
    """Async function with complex flow."""
    data = await fetch_multiple(urls)
    return ", ".join(data)


# ============================================================================
# 9. HIGHER-ORDER FUNCTIONS
# ============================================================================

def apply_twice(func: Callable[[int], int], value: int) -> int:
    """Applies function twice."""
    return func(func(value))


def compose(f: Callable, g: Callable) -> Callable:
    """Function composition."""
    return lambda x: f(g(x))


def filter_map_reduce(items: List[int],
                      predicate: Callable[[int], bool],
                      transformer: Callable[[int], int],
                      reducer: Callable[[int, int], int]) -> int:
    """Combines filter, map, and reduce."""
    filtered = filter(predicate, items)
    mapped = map(transformer, filtered)
    result = 0
    for item in mapped:
        result = reducer(result, item)
    return result


# ============================================================================
# 10. LAMBDA FUNCTIONS
# ============================================================================

# Lambdas in variables
square = lambda x: x ** 2
add_ten = lambda x: x + 10

# Lambda in dict
operations = {
    'double': lambda x: x * 2,
    'triple': lambda x: x * 3,
    'square': lambda x: x ** 2,
}


def use_lambda(op_name: str, value: int) -> int:
    """Uses lambda from dict."""
    return operations[op_name](value)


# ============================================================================
# 11. CONTEXT MANAGERS
# ============================================================================

class FileHandler:
    """Context manager class."""

    def __init__(self, filename: str):
        self.filename = filename
        self.file = None

    def __enter__(self):
        self.file = f"Opened {self.filename}"
        return self.file

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.file = None
        return False


# ============================================================================
# 12. COMPLEX CALL CHAINS
# ============================================================================

def chain_start(data: str) -> str:
    """Start of a 5-function call chain."""
    return chain_step1(data.upper())


def chain_step1(data: str) -> str:
    """Step 1 - calls step 2."""
    return chain_step2(data + "_1")


def chain_step2(data: str) -> str:
    """Step 2 - calls step 3."""
    return chain_step3(data + "_2")


def chain_step3(data: str) -> str:
    """Step 3 - calls step 4."""
    return chain_step4(data + "_3")


def chain_step4(data: str) -> str:
    """Step 4 - final step."""
    return data + "_DONE"


# ============================================================================
# 13. METHOD OVERRIDING
# ============================================================================

class Parent:
    """Base class with methods to override."""

    def method_a(self) -> str:
        return "Parent A"

    def method_b(self) -> str:
        return "Parent B"

    def method_c(self) -> str:
        """Calls other methods - tests override behavior."""
        return f"{self.method_a()} + {self.method_b()}"


class Child(Parent):
    """Overrides some methods."""

    def method_a(self) -> str:
        """Override method_a."""
        return "Child A"

    # method_b not overridden - uses parent version

    def method_d(self) -> str:
        """New method, calls inherited method."""
        return f"New: {self.method_c()}"


# ============================================================================
# 14. COMPLEX BRANCHING CALLS
# ============================================================================

def branching_caller(mode: str) -> str:
    """Calls different functions based on mode."""
    if mode == "A":
        return path_a()
    elif mode == "B":
        return path_b()
    else:
        return path_c()


def path_a() -> str:
    """Path A - calls helper_a."""
    return helper_a()


def path_b() -> str:
    """Path B - calls helper_b."""
    return helper_b()


def path_c() -> str:
    """Path C - calls both helpers."""
    return f"{helper_a()} and {helper_b()}"


def helper_a() -> str:
    return "A"


def helper_b() -> str:
    return "B"


# ============================================================================
# 15. ORCHESTRATOR - Complex call graph
# ============================================================================

def orchestrator() -> dict:
    """Main function that calls many others - creates complex graph."""

    # Abstract classes and multiple inheritance
    duck = Duck("Donald")
    duck_actions = duck.do_everything()  # Calls Animal.describe, Flyer.fly, Swimmer.swim

    dog = Dog("Rex")
    dog_sound = dog.make_sound()

    # Decorators
    calc = Calculator("main")
    calc_default = Calculator.create_default()  # Static method
    count = Calculator.get_count()  # Class method
    sum_result = calc.add(5, 3)  # Decorated method

    # Generics
    stack = Stack[int]()
    stack.push(1)
    stack.push(2)
    doubled_stack = stack.transform(lambda x: x * 2)

    # Closures
    times_5 = make_multiplier(5)
    mult_result = times_5(10)

    # Nested functions
    nested = deeply_nested(1)

    # Recursion
    fact = factorial(5)
    fib = fibonacci(8)

    # Mutual recursion
    even = is_even(10)
    odd = is_odd(9)

    # Generators
    gen_list = list(count_up_to(5))
    pipeline = list(generator_pipeline([1, 2, 3]))

    # Higher-order functions
    twice = apply_twice(lambda x: x + 1, 10)
    add_then_square = compose(square, add_ten)
    composed = add_then_square(5)

    # Lambda usage
    lambda_result = use_lambda('double', 7)

    # Call chains
    chain = chain_start("test")

    # Method overriding
    child = Child()
    override_test = child.method_d()

    # Branching
    branch_a = branching_caller("A")
    branch_b = branching_caller("B")
    branch_c = branching_caller("C")

    return {
        'duck': duck_actions,
        'dog': dog_sound,
        'calculator': sum_result,
        'count': count,
        'stack': doubled_stack.pop(),
        'closure': mult_result,
        'nested': nested,
        'factorial': fact,
        'fibonacci': fib,
        'even': even,
        'odd': odd,
        'generators': gen_list,
        'pipeline': pipeline,
        'hof': twice,
        'composed': composed,
        'lambda': lambda_result,
        'chain': chain,
        'override': override_test,
        'branches': [branch_a, branch_b, branch_c]
    }


# ============================================================================
# 16. ASYNC ORCHESTRATOR
# ============================================================================

async def async_orchestrator():
    """Async version with mixed async/sync calls."""
    urls = ["url1", "url2", "url3"]

    # Async calls
    async_data = await fetch_multiple(urls)
    processed = await process_async(urls)

    # Mix with sync
    sync_result = orchestrator()

    return {
        'async': async_data,
        'processed': processed,
        'sync': sync_result
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Running stress test...")

    # Sync execution
    result = orchestrator()
    print(f"Results: {len(result)} operations completed")

    # Async execution
    async_result = asyncio.run(async_orchestrator())
    print(f"Async complete")
