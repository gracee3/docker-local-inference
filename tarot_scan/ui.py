"""Interactive TUI for tarot scanning workflow."""

import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tarot_scan.config import DEFAULT_DPI, get_decks_dir
from tarot_scan.manifest import (
    append_record,
    get_classifications,
    get_crops,
    get_next_scan_id,
    get_pending_crops,
    get_scans,
)
from tarot_scan.models import ScanMeta


class TarotUI:
    """Interactive TUI state and rendering."""

    def __init__(self, deck_name: str | None = None):
        self.console = Console()
        self.status_message = ""
        self.last_scan_path: Path | None = None
        self.running = True

        # Initialize deck
        decks_dir = get_decks_dir()
        if deck_name:
            self.deck_dir = decks_dir / deck_name
        else:
            # Find most recent deck or create default
            existing = list(decks_dir.glob("*/manifest.jsonl"))
            if existing:
                self.deck_dir = max(existing, key=lambda p: p.stat().st_mtime).parent
            else:
                self.deck_dir = decks_dir / "deck_001"

        self.deck_dir.mkdir(parents=True, exist_ok=True)
        (self.deck_dir / "raw_scans").mkdir(exist_ok=True)
        (self.deck_dir / "extracted").mkdir(exist_ok=True)

        self.manifest_path = self.deck_dir / "manifest.jsonl"

    def get_stats(self) -> dict:
        """Get current deck statistics."""
        scans = get_scans(self.manifest_path)
        crops = get_crops(self.manifest_path)
        classifications = get_classifications(self.manifest_path)
        pending = get_pending_crops(self.manifest_path)

        return {
            "scans": len(scans),
            "cards": len(crops),
            "classified": len(classifications),
            "pending": len(pending),
        }

    def render(self) -> Panel:
        """Render the UI panel."""
        stats = self.get_stats()

        # Header
        header = Text()
        header.append("Tarot Scanner", style="bold cyan")
        header.append(" - Deck: ", style="dim")
        header.append(self.deck_dir.name, style="green")

        # Stats line
        stats_text = Text()
        stats_text.append(f"Scans: {stats['scans']}", style="blue")
        stats_text.append("  |  ", style="dim")
        stats_text.append(f"Cards: {stats['cards']}", style="green")
        stats_text.append("  |  ", style="dim")
        stats_text.append(f"Classified: {stats['classified']}", style="cyan")
        if stats["pending"] > 0:
            stats_text.append("  |  ", style="dim")
            stats_text.append(f"Pending: {stats['pending']}", style="yellow")

        # Commands table
        commands = Table(show_header=False, box=None, padding=(0, 2))
        commands.add_column("Key", style="cyan bold", width=5)
        commands.add_column("Action")

        commands.add_row("[s]", "Scan + Detect")
        commands.add_row("[r]", "Re-detect last scan")
        commands.add_row("[c]", f"Classify pending ({stats['pending']} cards)")
        commands.add_row("[n]", "New deck")
        commands.add_row("[l]", "List decks")
        commands.add_row("[h]", "Health check")
        commands.add_row("[q]", "Quit")

        # Status message
        status = Text()
        if self.status_message:
            status.append("\n")
            status.append(self.status_message)

        # Combine into panel
        content = Text()
        content.append(header)
        content.append("\n")
        content.append(stats_text)
        content.append("\n\n")

        panel = Panel(
            content,
            title="[bold]Tarot Scanner[/bold]",
            subtitle="Press key to act",
            border_style="blue",
        )

        return panel

    def set_status(self, message: str, style: str = ""):
        """Update status message."""
        if style:
            self.status_message = f"[{style}]{message}[/{style}]"
        else:
            self.status_message = message

    def do_scan(self):
        """Execute scan + detect workflow."""
        from tarot_scan.detect import detect_and_extract
        from tarot_scan.scanner import ScannerError, scan_to_path

        self.set_status("Starting scan...", "yellow")

        # Generate scan ID and filename
        scan_id = get_next_scan_id(self.manifest_path)
        timestamp = datetime.now()
        filename = f"{scan_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
        scan_path = self.deck_dir / "raw_scans" / filename

        try:
            # Scan
            self.console.print(f"  Scanning to {scan_path.name}...")
            scan_to_path(
                out_path=scan_path,
                dpi=DEFAULT_DPI,
                progress_callback=lambda msg: self.console.print(f"    {msg}"),
            )

            # Record scan in manifest
            from tarot_scan.scanner import get_default_device
            device = get_default_device()

            scan_meta = ScanMeta(
                scan_id=scan_id,
                file=f"raw_scans/{filename}",
                timestamp=timestamp,
                dpi=DEFAULT_DPI,
                device=device,
            )
            append_record(self.manifest_path, scan_meta)

            self.last_scan_path = scan_path

            # Detect cards
            self.console.print("  Detecting cards...")
            crops = detect_and_extract(
                scan_path=scan_path,
                deck_dir=self.deck_dir,
                scan_id=scan_id,
                debug=True,
                progress_callback=lambda msg: self.console.print(f"    {msg}"),
            )

            self.set_status(f"Scan complete: {len(crops)} cards detected", "green")

        except ScannerError as e:
            self.set_status(f"Scan failed: {e}", "red")
        except Exception as e:
            self.set_status(f"Error: {e}", "red")

    def do_redetect(self):
        """Re-run detection on last scan."""
        if not self.last_scan_path or not self.last_scan_path.exists():
            self.set_status("No previous scan to re-detect", "yellow")
            return

        from tarot_scan.detect import detect_and_extract
        from tarot_scan.manifest import get_next_scan_id

        self.set_status("Re-detecting...", "yellow")

        try:
            # Use a new scan ID for the re-detection
            scan_id = get_next_scan_id(self.manifest_path)

            self.console.print(f"  Re-detecting cards in {self.last_scan_path.name}...")
            crops = detect_and_extract(
                scan_path=self.last_scan_path,
                deck_dir=self.deck_dir,
                scan_id=scan_id,
                debug=True,
                progress_callback=lambda msg: self.console.print(f"    {msg}"),
            )

            self.set_status(f"Re-detection complete: {len(crops)} cards", "green")

        except Exception as e:
            self.set_status(f"Error: {e}", "red")

    def do_classify(self):
        """Classify pending crops."""
        from tarot_scan.classify import classify_crops

        stats = self.get_stats()
        if stats["pending"] == 0:
            self.set_status("No pending cards to classify", "yellow")
            return

        self.set_status(f"Classifying {stats['pending']} cards...", "yellow")

        try:
            results = classify_crops(
                deck_dir=self.deck_dir,
                pending_only=True,
                progress_callback=lambda msg: self.console.print(f"    {msg}"),
            )

            self.set_status(f"Classified {len(results)} cards", "green")

            # Print summary
            for r in results:
                self.console.print(
                    f"    {r.crop_id}: {r.result.card_name} ({r.result.confidence:.0%})"
                )

        except Exception as e:
            self.set_status(f"Classification error: {e}", "red")

    def do_new_deck(self):
        """Create a new deck."""
        # Find next deck number
        decks_dir = get_decks_dir()
        existing = list(decks_dir.glob("deck_*"))
        if existing:
            nums = [int(d.name.split("_")[1]) for d in existing if d.name.startswith("deck_")]
            next_num = max(nums) + 1 if nums else 1
        else:
            next_num = 1

        new_name = f"deck_{next_num:03d}"
        self.deck_dir = decks_dir / new_name
        self.deck_dir.mkdir(parents=True, exist_ok=True)
        (self.deck_dir / "raw_scans").mkdir(exist_ok=True)
        (self.deck_dir / "extracted").mkdir(exist_ok=True)
        self.manifest_path = self.deck_dir / "manifest.jsonl"
        self.last_scan_path = None

        self.set_status(f"Created new deck: {new_name}", "green")

    def do_list_decks(self):
        """List available decks."""
        decks_dir = get_decks_dir()
        decks = list(decks_dir.glob("*/manifest.jsonl"))

        if not decks:
            self.console.print("  No decks found")
            return

        self.console.print("\n  Available decks:")
        for manifest in sorted(decks):
            deck_dir = manifest.parent
            scans = len(get_scans(manifest))
            crops = len(get_crops(manifest))
            classifications = len(get_classifications(manifest))
            current = " (current)" if deck_dir == self.deck_dir else ""
            self.console.print(
                f"    {deck_dir.name}: {scans} scans, {crops} cards, "
                f"{classifications} classified{current}"
            )

    def do_health_check(self):
        """Check vLLM health."""
        from tarot_scan.vlm_client import health_check

        healthy, message = health_check()
        if healthy:
            self.set_status(f"VLM OK: {message}", "green")
        else:
            self.set_status(f"VLM Error: {message}", "red")

    def handle_key(self, key: str) -> bool:
        """Handle keypress. Returns False to quit."""
        if key == "q":
            return False
        elif key == "s":
            self.do_scan()
        elif key == "r":
            self.do_redetect()
        elif key == "c":
            self.do_classify()
        elif key == "n":
            self.do_new_deck()
        elif key == "l":
            self.do_list_decks()
        elif key == "h":
            self.do_health_check()
        return True


def get_key() -> str:
    """Read a single keypress (Unix-style)."""
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def run_ui(deck_name: str | None = None):
    """Run the interactive TUI."""
    ui = TarotUI(deck_name=deck_name)
    console = Console()

    console.print("\n[bold cyan]Tarot Scanner TUI[/bold cyan]")
    console.print(f"Deck: [green]{ui.deck_dir.name}[/green]")
    console.print()

    # Print menu
    console.print("[cyan bold][s][/cyan bold] Scan + Detect")
    console.print("[cyan bold][r][/cyan bold] Re-detect last scan")
    console.print("[cyan bold][c][/cyan bold] Classify pending")
    console.print("[cyan bold][n][/cyan bold] New deck")
    console.print("[cyan bold][l][/cyan bold] List decks")
    console.print("[cyan bold][h][/cyan bold] Health check")
    console.print("[cyan bold][q][/cyan bold] Quit")
    console.print()

    # Show initial stats
    stats = ui.get_stats()
    console.print(
        f"Stats: {stats['scans']} scans, {stats['cards']} cards, "
        f"{stats['classified']} classified, {stats['pending']} pending"
    )
    console.print()

    while ui.running:
        console.print("[dim]Press key: [/dim]", end="")
        try:
            key = get_key()
            console.print(key)  # Echo the key

            if key == "\x03":  # Ctrl+C
                break

            if not ui.handle_key(key):
                break

            # Refresh stats
            if key in ("s", "r", "c", "n"):
                stats = ui.get_stats()
                console.print(
                    f"\nStats: {stats['scans']} scans, {stats['cards']} cards, "
                    f"{stats['classified']} classified, {stats['pending']} pending\n"
                )

        except KeyboardInterrupt:
            break

    console.print("\n[dim]Goodbye![/dim]")
