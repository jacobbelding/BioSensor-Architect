"""Command-line interface for BioSensor-Architect."""

import asyncio
import re
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
def main():
    """BioSensor-Architect: Multi-agent genetic construct designer."""
    pass


@main.command()
@click.argument("query")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output HTML file path.")
@click.option("--model", "-m", default=None, help="LLM model override (e.g., gpt-4o-mini).")
@click.option(
    "--rounds", "-r", default=None, type=int,
    help="Number of design rounds (default from DESIGN_ROUNDS env var, default=1). Extra rounds ~double token cost.",
)
@click.option("--verbose", "-v", is_flag=True, help="Show each agent's message as it's produced.")
def run(query: str, output: str | None, model: str | None, rounds: int | None, verbose: bool):
    """Run a full design workflow for the given query.

    Example: bsa run "design a nitrate sensor for Arabidopsis"
    """
    console.print(Panel(f"[bold]Query:[/bold] {query}", title="BioSensor-Architect", border_style="green"))
    console.print()

    rounds_label = f" ({rounds} round{'s' if rounds and rounds > 1 else ''})" if rounds and rounds > 1 else ""
    with console.status(f"[bold green]Running multi-agent design workflow{rounds_label}...", spinner="dots"):
        from biosensor_architect.orchestration.workflow import run_workflow

        final = asyncio.run(run_workflow(query, model=model, rounds=rounds))

    if not final:
        console.print("[red]No output produced by the workflow.[/]")
        return

    # Determine output path
    if output is None:
        slug = re.sub(r"[^a-z0-9]+", "_", query.lower())[:50].strip("_")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{slug}.html"
    else:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Wrap in basic HTML if the output isn't already HTML
    if "<html" in final.lower() or "<!doctype" in final.lower():
        html_out = final
    else:
        style = "font-family: system-ui; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6;"
        html_out = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>BioSensor-Architect Report</title>
<style>body {{ {style} }}</style>
</head><body>
<h1>BioSensor-Architect Report</h1>
<pre style="white-space: pre-wrap;">{final}</pre>
</body></html>"""

    output_path.write_text(html_out)
    console.print(f"\n[bold green]✓ Report saved to:[/] {output_path}")
    console.print(f"[dim]  Open in browser: file://{output_path.resolve()}[/]")

    # Quick sanity check
    has_html = "<html" in final.lower()
    has_svg = "<svg" in final.lower()
    console.print(f"[dim]  Contains HTML: {has_html} | Contains SVG: {has_svg} | Length: {len(final):,} chars[/]")


@main.command()
@click.argument("identifiers")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.option("--model", "-m", default=None, help="LLM model override.")
def ingest(identifiers: str, yes: bool, model: str | None):
    """Ingest papers by PMID or DOI into the parts catalog and pathway database.

    IDENTIFIERS can be a single ID or comma-separated list.

    \b
    Examples:
        bsa ingest "PMID:11050181"
        bsa ingest "DOI:10.1038/s41477-021-00866-5"
        bsa ingest "PMID:11050181,PMID:17259264"
    """
    from biosensor_architect.tools.paper_ingest import (
        append_to_catalog,
        append_to_pathways,
        deduplicate_parts,
        deduplicate_pathways,
        extract_parts_from_paper,
        load_catalog,
        load_pathways,
        resolve_identifier,
    )

    id_list = [i.strip() for i in identifiers.split(",") if i.strip()]
    console.print(f"[bold green]Ingesting {len(id_list)} paper(s)...[/]\n")

    all_new_parts: list[dict] = []
    all_new_pathways: list[dict] = []

    for identifier in id_list:
        console.print(f"[bold]Resolving:[/] {identifier}")
        try:
            metadata = resolve_identifier(identifier)
        except ValueError as e:
            console.print(f"  [red]Error: {e}[/]")
            continue

        console.print(f"  [dim]Title:[/] {metadata.get('title', 'Unknown')}")
        console.print(f"  [dim]Authors:[/] {', '.join(metadata.get('authors', [])[:3])}")
        console.print(f"  [dim]Year:[/] {metadata.get('year', '?')}")

        console.print("  [dim]Extracting parts and pathways via LLM...[/]")
        extracted = asyncio.run(extract_parts_from_paper(metadata, model=model))

        parts = extracted.get("parts", [])
        pathways = extracted.get("pathways", [])
        console.print(f"  [green]Found {len(parts)} part(s) and {len(pathways)} pathway(s)[/]")

        all_new_parts.extend(parts)
        all_new_pathways.extend(pathways)

    if not all_new_parts and not all_new_pathways:
        console.print("\n[yellow]No new parts or pathways extracted.[/]")
        return

    # Deduplicate against existing data
    existing_parts = load_catalog()
    existing_pathways = load_pathways()

    unique_parts = deduplicate_parts(all_new_parts, existing_parts)
    unique_pathways = deduplicate_pathways(all_new_pathways, existing_pathways)

    if not unique_parts and not unique_pathways:
        console.print("\n[yellow]All extracted items already exist in the catalog.[/]")
        return

    # Show what will be added
    if unique_parts:
        console.print(f"\n[bold green]New parts to add ({len(unique_parts)}):[/]")
        parts_table = Table(show_lines=True)
        parts_table.add_column("ID", width=15)
        parts_table.add_column("Name", width=30)
        parts_table.add_column("Type", width=12)
        parts_table.add_column("Organism", width=20)
        for p in unique_parts:
            parts_table.add_row(p.get("id", "?"), p.get("name", "?"), p.get("type", "?"), p.get("organism", "?"))
        console.print(parts_table)

    if unique_pathways:
        console.print(f"\n[bold green]New pathways to add ({len(unique_pathways)}):[/]")
        for pw in unique_pathways:
            sig = pw.get('signal', '?')
            org = pw.get('organism', '?')
            desc = pw.get('description', '')[:80]
            console.print(f"  [bold]{sig}[/] in {org}: {desc}")

    # Confirm
    if not yes:
        if not click.confirm("\nAdd these to the database?"):
            console.print("[yellow]Aborted.[/]")
            return

    # Append
    n_parts = append_to_catalog(unique_parts)
    n_pathways = append_to_pathways(unique_pathways)
    console.print(f"\n[bold green]Done![/] Added {n_parts} part(s) and {n_pathways} pathway(s).")


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
