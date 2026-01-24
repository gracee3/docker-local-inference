"""Typer CLI for tarot-scan commands."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from tarot_scan.config import (
    DEFAULT_DPI,
    DEFAULT_EPSILON_FRAC,
    DEFAULT_MAX_AREA_FRAC,
    DEFAULT_MIN_AREA_FRAC,
    DEFAULT_SCAN_FORMAT,
    DEFAULT_SCAN_MODE,
    DEFAULT_TARGET_HEIGHT,
    get_decks_dir,
)

app = typer.Typer(
    name="tarot-scan",
    help="Tarot card scanner, detector, and classifier toolkit",
    no_args_is_help=True,
)
console = Console()


@app.command("list-devices")
def list_devices_cmd():
    """List available SANE scanner devices."""
    from tarot_scan.scanner import ScannerError, list_devices

    try:
        devices = list_devices()
    except ScannerError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not devices:
        console.print("[yellow]No scanners detected.[/yellow]")
        console.print("Check that your scanner is connected and powered on.")
        raise typer.Exit(1)

    table = Table(title="Available Scanners")
    table.add_column("Device String", style="cyan")
    table.add_column("Description", style="green")

    for d in devices:
        table.add_row(d.device_string, d.description)

    console.print(table)
    console.print("\nUse [cyan]--device[/cyan] to select, or set [cyan]SANE_DEVICE[/cyan] env var.")


@app.command("scan")
def scan_cmd(
    out: Annotated[Optional[Path], typer.Option(help="Output file path")] = None,
    device: Annotated[Optional[str], typer.Option(help="Scanner device string")] = None,
    dpi: Annotated[int, typer.Option(help="Scan resolution")] = DEFAULT_DPI,
    mode: Annotated[str, typer.Option(help="Color mode (Color, Gray)")] = DEFAULT_SCAN_MODE,
    fmt: Annotated[str, typer.Option(help="Output format (png, tiff)")] = DEFAULT_SCAN_FORMAT,
):
    """Scan from flatbed to file."""
    from tarot_scan.scanner import ScannerError, scan_to_path

    # Default output path
    if out is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = Path(f"scan_{timestamp}.{fmt}")

    console.print(f"Scanning to [cyan]{out}[/cyan]...")

    try:
        result = scan_to_path(
            out_path=out,
            device=device,
            dpi=dpi,
            mode=mode,
            fmt=fmt,
            progress_callback=lambda msg: console.print(f"  {msg}"),
        )
        console.print(f"[green]Scan saved:[/green] {result}")
        console.print(f"Size: {result.stat().st_size / (1024 * 1024):.1f} MB")
    except ScannerError as e:
        console.print(f"[red]Scan failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("detect")
def detect_cmd(
    scan: Annotated[Path, typer.Argument(help="Path to scan image")],
    outdir: Annotated[Path, typer.Option(help="Output deck directory")] = None,
    scan_id: Annotated[Optional[str], typer.Option(help="Scan ID for manifest")] = None,
    min_area: Annotated[float, typer.Option(help="Min card area fraction")] = DEFAULT_MIN_AREA_FRAC,
    max_area: Annotated[float, typer.Option(help="Max card area fraction")] = DEFAULT_MAX_AREA_FRAC,
    epsilon: Annotated[float, typer.Option(help="Contour epsilon fraction")] = DEFAULT_EPSILON_FRAC,
    height: Annotated[int, typer.Option(help="Target crop height")] = DEFAULT_TARGET_HEIGHT,
    debug: Annotated[bool, typer.Option(help="Save debug annotated image")] = False,
):
    """Detect and extract cards from a scan image."""
    from tarot_scan.detect import detect_and_extract

    if not scan.exists():
        console.print(f"[red]Error:[/red] Scan file not found: {scan}")
        raise typer.Exit(1)

    # Default output directory
    if outdir is None:
        outdir = get_decks_dir() / "default"

    # Default scan ID
    if scan_id is None:
        from tarot_scan.manifest import get_next_scan_id
        manifest_path = outdir / "manifest.jsonl"
        scan_id = get_next_scan_id(manifest_path)

    console.print(f"Detecting cards in [cyan]{scan}[/cyan]...")

    try:
        crops = detect_and_extract(
            scan_path=scan,
            deck_dir=outdir,
            scan_id=scan_id,
            min_area_frac=min_area,
            max_area_frac=max_area,
            epsilon_frac=epsilon,
            target_height=height,
            debug=debug,
            progress_callback=lambda msg: console.print(f"  {msg}"),
        )

        console.print(f"[green]Extracted {len(crops)} cards[/green]")
        for crop in crops:
            console.print(f"  - {crop.crop_id}: {crop.file}")

    except Exception as e:
        console.print(f"[red]Detection failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("classify")
def classify_cmd(
    deck: Annotated[Path, typer.Option(help="Deck directory")] = None,
    pending_only: Annotated[bool, typer.Option(help="Only classify pending crops")] = True,
    max_cards: Annotated[Optional[int], typer.Option("--max", help="Max cards to process")] = None,
    resize: Annotated[int, typer.Option(help="Resize height for VLM")] = DEFAULT_TARGET_HEIGHT,
    model: Annotated[Optional[str], typer.Option(help="VLM model ID")] = None,
):
    """Classify extracted card crops using VLM."""
    from tarot_scan.classify import classify_crops

    if deck is None:
        deck = get_decks_dir() / "default"

    if not deck.exists():
        console.print(f"[red]Error:[/red] Deck directory not found: {deck}")
        raise typer.Exit(1)

    console.print(f"Classifying cards in [cyan]{deck}[/cyan]...")

    try:
        results = classify_crops(
            deck_dir=deck,
            pending_only=pending_only,
            max_cards=max_cards,
            resize_height=resize,
            model=model,
            progress_callback=lambda msg: console.print(f"  {msg}"),
        )

        console.print(f"\n[green]Classified {len(results)} cards[/green]")

        if results:
            table = Table(title="Classification Results")
            table.add_column("Crop ID", style="cyan")
            table.add_column("Card Name", style="green")
            table.add_column("Arcana")
            table.add_column("Confidence")

            for r in results:
                table.add_row(
                    r.crop_id,
                    r.result.card_name,
                    r.result.arcana,
                    f"{r.result.confidence:.0%}",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Classification failed:[/red] {e}")
        raise typer.Exit(1)


@app.command("health")
def health_cmd():
    """Check vLLM server health."""
    from tarot_scan.vlm_client import health_check

    healthy, message = health_check()

    if healthy:
        console.print(f"[green]✓[/green] {message}")
    else:
        console.print(f"[red]✗[/red] {message}")
        raise typer.Exit(1)


@app.command("ui")
def ui_cmd(
    deck: Annotated[Optional[str], typer.Option(help="Deck name to open/create")] = None,
):
    """Launch interactive TUI for scanning workflow."""
    from tarot_scan.ui import run_ui

    run_ui(deck_name=deck)


@app.command("classify-image")
def classify_image_cmd(
    image: Annotated[Path, typer.Argument(help="Path to image file")],
    model: Annotated[Optional[str], typer.Option(help="VLM model ID")] = None,
    resize: Annotated[int, typer.Option(help="Resize height")] = DEFAULT_TARGET_HEIGHT,
):
    """Classify a single image file (for testing)."""
    from tarot_scan.classify import classify_single

    if not image.exists():
        console.print(f"[red]Error:[/red] Image not found: {image}")
        raise typer.Exit(1)

    console.print(f"Classifying [cyan]{image}[/cyan]...")

    result = classify_single(
        image_path=image,
        model=model,
        resize_height=resize,
        progress_callback=lambda msg: console.print(f"  {msg}"),
    )

    if result:
        console.print("\n[green]Classification Result:[/green]")
        console.print(f"  Card: [cyan]{result.result.card_name}[/cyan]")
        console.print(f"  Arcana: {result.result.arcana}")
        if result.result.suit:
            console.print(f"  Suit: {result.result.suit}")
        if result.result.rank:
            console.print(f"  Rank: {result.result.rank}")
        if result.result.major_number is not None:
            console.print(f"  Major #: {result.result.major_number}")
        console.print(f"  Orientation: {result.result.orientation}")
        console.print(f"  Confidence: {result.result.confidence:.0%}")
        if result.result.notes:
            console.print(f"  Notes: {result.result.notes}")
        if result.result.deck_hint:
            console.print(f"  Deck hint: {result.result.deck_hint}")
    else:
        console.print("[red]Classification failed[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
