"""Command-line interface for CodeGraph."""

import click
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint
import json

from .db import CodeGraphDB
from .parser import PythonParser
from .builder import GraphBuilder
from .query import QueryInterface
from .validators import ConservationValidator

console = Console()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@click.group()
@click.option('--uri', default='bolt://localhost:7687', help='Neo4j URI')
@click.option('--user', default='neo4j', help='Neo4j username')
@click.option('--password', default='password', help='Neo4j password')
@click.pass_context
def cli(ctx, uri, user, password):
    """CodeGraph - A graph database for Python codebases with conservation laws."""
    ctx.ensure_object(dict)
    ctx.obj['db'] = CodeGraphDB(uri, user, password)
    ctx.obj['query'] = QueryInterface(ctx.obj['db'])
    ctx.obj['validator'] = ConservationValidator(ctx.obj['db'])


@cli.command()
@click.argument('path')
@click.option('--clear', is_flag=True, help='Clear database before indexing')
@click.pass_context
def index(ctx, path, clear):
    """Index a Python file or directory into the graph database."""
    db = ctx.obj['db']

    if clear:
        console.print("[yellow]Clearing database...[/yellow]")
        db.clear_database()

    console.print(f"[green]Initializing schema...[/green]")
    db.initialize_schema()

    console.print(f"[green]Parsing Python code at {path}...[/green]")
    parser = PythonParser()

    import os
    if os.path.isfile(path):
        entities, relationships = parser.parse_file(path)
    else:
        entities, relationships = parser.parse_directory(path)

    console.print(f"[cyan]Found {len(entities)} entities and {len(relationships)} relationships[/cyan]")

    console.print("[green]Building graph...[/green]")
    builder = GraphBuilder(db)
    builder.build_graph(entities, relationships)

    # Get statistics
    stats = db.get_statistics()

    table = Table(title="Database Statistics")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="magenta")

    for node_type, count in stats.items():
        table.add_row(node_type, str(count))

    console.print(table)
    console.print("[green]✓ Indexing complete![/green]")


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate the codebase against conservation laws."""
    validator = ctx.obj['validator']

    console.print("[green]Running conservation law validation...[/green]")

    with console.status("[bold green]Validating..."):
        report = validator.get_validation_report()

    # Display summary
    summary_table = Table(title="Validation Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="magenta")

    summary_table.add_row("Total Violations", str(report['total_violations']))
    summary_table.add_row("Errors", f"[red]{report['errors']}[/red]")
    summary_table.add_row("Warnings", f"[yellow]{report['warnings']}[/yellow]")

    console.print(summary_table)

    # Display by conservation law
    law_table = Table(title="Violations by Conservation Law")
    law_table.add_column("Law", style="cyan")
    law_table.add_column("Violations", style="magenta")

    law_table.add_row("1. Signature Conservation", str(report['summary']['signature_conservation']))
    law_table.add_row("2. Reference Integrity", str(report['summary']['reference_integrity']))
    law_table.add_row("3. Data Flow Consistency", str(report['summary']['data_flow_consistency']))
    law_table.add_row("4. Structural Integrity", str(report['summary']['structural_integrity']))

    console.print(law_table)

    # Display violations
    if report['violations']:
        console.print("\n[bold red]Violations:[/bold red]")
        for i, violation in enumerate(report['violations'][:20], 1):  # Show first 20
            severity_color = "red" if violation.severity == "error" else "yellow"
            console.print(f"\n[{severity_color}]{i}. {violation.message}[/{severity_color}]")
            console.print(f"   Type: {violation.violation_type.value}")
            console.print(f"   Entity: {violation.entity_id}")
            if violation.suggested_fix:
                console.print(f"   [cyan]Fix: {violation.suggested_fix}[/cyan]")

        if len(report['violations']) > 20:
            console.print(f"\n[yellow]... and {len(report['violations']) - 20} more violations[/yellow]")
    else:
        console.print("\n[green]✓ No violations found![/green]")


@cli.command()
@click.argument('function_name')
@click.pass_context
def find_function(ctx, function_name):
    """Find a function by name."""
    query = ctx.obj['query']

    functions = query.find_function(name=function_name)

    if not functions:
        console.print(f"[red]No functions found with name '{function_name}'[/red]")
        return

    for func in functions:
        console.print(Panel(
            f"[cyan]Name:[/cyan] {func['name']}\n"
            f"[cyan]Qualified Name:[/cyan] {func['qualified_name']}\n"
            f"[cyan]Signature:[/cyan] {func.get('signature', 'N/A')}\n"
            f"[cyan]Location:[/cyan] {func['location']}\n"
            f"[cyan]Visibility:[/cyan] {func.get('visibility', 'public')}",
            title=f"Function: {func['name']}",
            expand=False
        ))


@cli.command()
@click.argument('function_id')
@click.pass_context
def callers(ctx, function_id):
    """Find all callers of a function."""
    query = ctx.obj['query']

    callers = query.find_callers(function_id)

    if not callers:
        console.print(f"[yellow]No callers found for function {function_id}[/yellow]")
        return

    table = Table(title=f"Callers of {function_id}")
    table.add_column("Caller", style="cyan")
    table.add_column("Args", style="magenta")
    table.add_column("Location", style="green")

    for caller_info in callers:
        caller = caller_info['caller']
        table.add_row(
            caller['qualified_name'],
            str(caller_info.get('arg_count', 'N/A')),
            caller_info.get('location', 'N/A')
        )

    console.print(table)


@cli.command()
@click.argument('function_id')
@click.option('--depth', default=1, help='Depth of dependency traversal')
@click.pass_context
def dependencies(ctx, function_id, depth):
    """Show function dependencies."""
    query = ctx.obj['query']

    deps = query.get_function_dependencies(function_id, depth)

    # Outbound dependencies
    if deps['outbound']:
        out_table = Table(title="Functions Called (Outbound)")
        out_table.add_column("Function", style="cyan")
        out_table.add_column("Distance", style="magenta")

        for dep in deps['outbound']:
            out_table.add_row(
                dep['function']['qualified_name'],
                str(dep['distance'])
            )

        console.print(out_table)
    else:
        console.print("[yellow]No outbound dependencies[/yellow]")

    # Inbound dependencies
    if deps['inbound']:
        in_table = Table(title="Called By (Inbound)")
        in_table.add_column("Function", style="cyan")
        in_table.add_column("Distance", style="magenta")

        for dep in deps['inbound']:
            in_table.add_row(
                dep['function']['qualified_name'],
                str(dep['distance'])
            )

        console.print(in_table)
    else:
        console.print("[yellow]No inbound dependencies[/yellow]")


@cli.command()
@click.argument('entity_id')
@click.option('--change-type', default='modify', help='Change type: modify, delete, rename')
@click.pass_context
def impact(ctx, entity_id, change_type):
    """Analyze the impact of changing an entity."""
    query = ctx.obj['query']

    impact = query.get_impact_analysis(entity_id, change_type)

    console.print(Panel(
        f"[cyan]Entity:[/cyan] {entity_id}\n"
        f"[cyan]Change Type:[/cyan] {change_type}",
        title="Impact Analysis",
        expand=False
    ))

    if impact['affected_callers']:
        console.print(f"\n[yellow]Affected Callers: {len(impact['affected_callers'])}[/yellow]")
        for caller in impact['affected_callers'][:10]:
            console.print(f"  - {caller['caller']['qualified_name']}")

    if impact['affected_references']:
        console.print(f"\n[yellow]Affected References: {len(impact['affected_references'])}[/yellow]")

    if impact['cascading_changes']:
        console.print(f"\n[red]Cascading Changes Required:[/red]")
        for change in impact['cascading_changes']:
            console.print(f"  - {change['rel_type']}: {change['count']} {change['labels']}")


@cli.command()
@click.argument('pattern')
@click.option('--type', 'entity_type', help='Entity type: Function, Class, Variable')
@click.pass_context
def search(ctx, pattern, entity_type):
    """Search for entities by pattern."""
    query = ctx.obj['query']

    results = query.search_by_pattern(pattern, entity_type)

    if not results:
        console.print(f"[yellow]No entities found matching '{pattern}'[/yellow]")
        return

    table = Table(title=f"Search Results: '{pattern}'")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Qualified Name", style="green")

    for result in results[:50]:  # Limit to 50 results
        node = result['node']
        labels = result['labels']
        table.add_row(
            labels[0] if labels else "Unknown",
            node.get('name', 'N/A'),
            node.get('qualified_name', 'N/A')
        )

    console.print(table)

    if len(results) > 50:
        console.print(f"[yellow]... and {len(results) - 50} more results[/yellow]")


@cli.command()
@click.pass_context
def stats(ctx):
    """Show database statistics."""
    db = ctx.obj['db']

    stats = db.get_statistics()

    table = Table(title="Database Statistics")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="magenta")

    for node_type, count in stats.items():
        table.add_row(node_type, str(count))

    console.print(table)


@cli.command()
@click.argument('query_string')
@click.option('--format', 'output_format', default='table', help='Output format: table, json')
@click.pass_context
def query(ctx, query_string, output_format):
    """Execute a raw Cypher query."""
    db = ctx.obj['db']

    try:
        results = db.execute_query(query_string)

        if output_format == 'json':
            console.print(json.dumps(results, indent=2))
        else:
            if results:
                # Create table from first result to get columns
                table = Table(title="Query Results")
                for key in results[0].keys():
                    table.add_column(key, style="cyan")

                for record in results[:100]:  # Limit to 100 rows
                    table.add_row(*[str(v) for v in record.values()])

                console.print(table)

                if len(results) > 100:
                    console.print(f"[yellow]... and {len(results) - 100} more results[/yellow]")
            else:
                console.print("[yellow]No results[/yellow]")

    except Exception as e:
        console.print(f"[red]Query error: {e}[/red]")


def main():
    """Main entry point."""
    cli(obj={})


if __name__ == '__main__':
    main()
