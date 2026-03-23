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
@click.option("--verbose", "-v", is_flag=True, help="Show each agent's message as it's produced.")
def run(query: str, output: str | None, model: str | None, verbose: bool):
    """Run a full design workflow for the given query.

    Example: bsa run "design a nitrate sensor for Arabidopsis"
    """
    console.print(Panel(f"[bold]Query:[/bold] {query}", title="BioSensor-Architect", border_style="green"))
    console.print()

    async def _run():
        from biosensor_architect.orchestration.workflow import build_workflow

        team = await build_workflow(model=model)
        result = await team.run(task=query)

        if verbose:
            # Print a summary table of all agent messages
            table = Table(title="Agent Conversation Log", show_lines=True)
            table.add_column("#", style="dim", width=3)
            table.add_column("Agent", style="bold", width=25)
            table.add_column("Content (first 120 chars)", width=80)

            for i, msg in enumerate(result.messages):
                source = getattr(msg, "source", "system")
                content = getattr(msg, "content", "")
                if isinstance(content, str):
                    preview = content[:120].replace("\n", " ")
                elif isinstance(content, list):
                    preview = f"[{len(content)} tool call(s)]"
                else:
                    preview = str(content)[:120]
                table.add_row(str(i), str(source), preview)

            console.print()
            console.print(table)

        return result

    with console.status("[bold green]Running multi-agent design workflow...", spinner="dots"):
        result = asyncio.run(_run())

    # Extract HTML report using the same logic as run_workflow
    html_content = ""
    documenter_content = ""
    longest_content = ""

    for msg in result.messages:
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        source = getattr(msg, "source", "")

        if ("<!doctype" in content.lower() or "<html" in content.lower()) and len(content) > len(html_content):
            html_content = content
        if source == "Documenter" and len(content) > len(documenter_content):
            documenter_content = content
        if len(content) > len(longest_content):
            longest_content = content

    final = html_content or documenter_content or longest_content

    if not final:
        console.print("[red]No output produced by the workflow.[/]")
        return

    # Strip anything after </html>
    if "</html>" in final.lower():
        idx = final.lower().index("</html>") + len("</html>")
        final = final[:idx]

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
        html_out = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>BioSensor-Architect Report</title>
<style>body {{ font-family: system-ui; max-width: 900px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}</style>
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
