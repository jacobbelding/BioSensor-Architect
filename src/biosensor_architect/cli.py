"""Command-line interface for BioSensor-Architect."""

import click
from rich.console import Console

console = Console()


@click.group()
def main():
    """BioSensor-Architect: Multi-agent genetic construct designer."""
    pass


@main.command()
@click.argument("query")
def run(query: str):
    """Run a full design workflow for the given query.

    Example: bsa run "design a nitrate sensor for Arabidopsis"
    """
    console.print(f"[bold green]Starting design workflow for:[/] {query}")
    # TODO: Wire up orchestration workflow
    console.print("[yellow]Not yet implemented — see orchestration/workflow.py[/]")


@main.command()
@click.argument("path", type=click.Path(exists=True))
def index_papers(path: str):
    """Index papers from a directory into the RAG database.

    Example: bsa index-papers ./papers/
    """
    console.print(f"[bold green]Indexing papers from:[/] {path}")
    # TODO: Wire up RAG indexer
    console.print("[yellow]Not yet implemented — see rag/indexer.py[/]")


@main.command()
def serve():
    """Start the MCP servers."""
    console.print("[bold green]Starting MCP servers...[/]")
    # TODO: Launch MCP server processes
    console.print("[yellow]Not yet implemented — see mcp_servers/[/]")


if __name__ == "__main__":
    main()
