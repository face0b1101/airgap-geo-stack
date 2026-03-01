"""Prepare all data required by the airgap-geo-stack Docker services.

Downloads an OSM PBF extract and processes it for Nominatim, OSRM (car, foot,
bike), and optionally downloads the Photon European geocoding dataset (~60 GB).

Set PBF_URL and PBF_REGION in your .env file to change the region.  Browse
https://download.geofabrik.de to find your extract.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console
from rich.markup import escape as rich_escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

app = typer.Typer(
    name="prepare-data",
    help="Download and process geodata for the airgap-geo-stack Docker services.",
    no_args_is_help=False,
)

console = Console()

DOCKER_DIR = Path(__file__).resolve().parents[3] / "docker"

PROFILES = {"car": "car", "foot": "foot", "bike": "bicycle"}

_TAIL_LINES = 20

_OOM_EXIT_CODE = 137


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_elapsed(seconds: float) -> str:
    """Format *seconds* as ``Xm Ys`` or ``Xs``."""
    mins, secs = divmod(int(seconds), 60)
    if mins:
        return f"{mins}m {secs}s"
    return f"{secs}s"


def _dir_size(path: Path) -> int:
    """Return total size in bytes of all files under *path*."""
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:
        return 0


def _check_docker() -> None:
    """Verify that the Docker daemon is reachable."""
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        console.print(
            Panel(
                "[bold red]Docker is not available.[/]\n\n"
                "Ensure Docker Desktop (or the Docker daemon) is running and\n"
                "that the [cyan]docker[/] CLI is on your PATH.",
                title="Pre-flight check failed",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def _run_docker(
    args: list[str],
    *,
    label: str,
    verbose: bool = False,
    allow_oom: bool = False,
) -> int:
    """Run a ``docker run`` command, streaming output with a spinner.

    In *verbose* mode every line is printed directly.  Otherwise a Rich
    spinner shows the latest line plus elapsed time.  On failure the last
    captured output lines are printed alongside a copy-pasteable command.

    Returns the process exit code.  When *allow_oom* is ``True`` and the
    container is OOM-killed (exit 137), the error is printed but no
    exception is raised — the caller can inspect the return value and retry.
    """
    cmd = ["docker", "run", "--rm", *args]
    tail: deque[str] = deque(maxlen=_TAIL_LINES)
    t0 = time.monotonic()

    if verbose:
        console.print(f"  [bold cyan]{label}[/]")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            stripped = line.rstrip()
            tail.append(stripped)
            console.print(f"    {rich_escape(stripped)}")
        returncode = proc.wait()
    else:
        with console.status(f"[bold cyan]{label}[/]") as status:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                stripped = line.rstrip()
                tail.append(stripped)
                elapsed = _fmt_elapsed(time.monotonic() - t0)
                status.update(
                    f"[bold cyan]{label}[/] [dim]({elapsed})[/]  "
                    f"{rich_escape(stripped)}"
                )
            returncode = proc.wait()

    if returncode != 0:
        console.print(
            f"[bold red]Command failed (exit {returncode}):[/]\n  {shlex.join(cmd)}"
        )
        if tail:
            console.print("[dim]Last output lines:[/]")
            for ln in tail:
                console.print(f"  {rich_escape(ln)}")
        if allow_oom and returncode == _OOM_EXIT_CODE:
            return returncode
        raise typer.Exit(code=returncode)

    return returncode


def _download_file(url: str, dest: Path) -> None:
    """Download *url* to *dest* with resume support and a Rich progress bar."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    headers: dict[str, str] = {}
    existing_bytes = 0
    if dest.exists():
        existing_bytes = dest.stat().st_size
        headers["Range"] = f"bytes={existing_bytes}-"

    with httpx.stream(
        "GET", url, headers=headers, follow_redirects=True, timeout=60
    ) as resp:
        if resp.status_code == 416:
            console.print(f"  [green]Already fully downloaded:[/] {dest}")
            return

        resp.raise_for_status()

        is_resume = resp.status_code == 206
        total_size: int | None = None
        if content_length := resp.headers.get("content-length"):
            total_size = int(content_length) + (existing_bytes if is_resume else 0)

        mode = "ab" if is_resume else "wb"
        with (
            Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress,
            dest.open(mode) as fh,
        ):
            task = progress.add_task(
                f"Downloading [cyan]{dest.name}[/]",
                total=total_size,
                completed=existing_bytes,
            )
            for chunk in resp.iter_bytes(chunk_size=1024 * 256):
                fh.write(chunk)
                progress.advance(task, len(chunk))


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


class StepResult:
    """Tracks the outcome of a single preparation step.

    Attributes:
        name: Human-readable step label.
        status: One of ``pending``, ``completed``, ``skipped``, or ``failed``.
        elapsed: Wall-clock seconds the step took.
    """

    def __init__(self, name: str) -> None:  # noqa: D107
        self.name = name
        self.status = "pending"
        self.elapsed: float = 0.0

    def mark(self, status: str, elapsed: float) -> None:
        """Record the final *status* and *elapsed* time for this step."""
        self.status = status
        self.elapsed = elapsed


def _step_download_pbf(
    *,
    force: bool,
    pbf_url: str,
    pbf_dest: Path,
) -> StepResult:
    """Step 1 — download OSM PBF extract."""
    result = StepResult("Download PBF")
    t0 = time.monotonic()

    pbf_dest.parent.mkdir(parents=True, exist_ok=True)

    if pbf_dest.exists() and not force:
        console.print(f"  [green]PBF already present:[/] {pbf_dest}")
        result.mark("completed", time.monotonic() - t0)
        return result

    _download_file(pbf_url, pbf_dest)
    console.print(f"  [green]PBF ready:[/] {pbf_dest}")
    result.mark("completed", time.monotonic() - t0)
    return result


def _step_osrm_profile(
    profile: str,
    *,
    force: bool,
    cleanup: bool,
    threads: int,
    pbf_name: str,
    pbf_region: str,
    pbf_source: Path,
    osrm_image: str,
    osrm_platform: str,
    verbose: bool = False,
) -> StepResult:
    """Step 2 — OSRM extract/partition/customise for a single profile."""
    result = StepResult(f"OSRM {profile}")
    t0 = time.monotonic()

    profile_dir = DOCKER_DIR / "osrm" / "data" / profile
    osrm_base = profile_dir / f"{pbf_region}-latest.osrm"
    profile_dir.mkdir(parents=True, exist_ok=True)

    console.rule(f"[bold]OSRM profile: {profile}[/]")

    if not force and osrm_base.with_suffix(".osrm.mldgr").exists():
        console.print(
            f"  Profile [cyan]{profile}[/] already complete "
            "(found .osrm.mldgr), skipping."
        )
        result.mark("skipped", time.monotonic() - t0)
        return result

    pbf_copy = profile_dir / pbf_name
    if not pbf_copy.exists():
        console.print(f"  Copying PBF to [cyan]{profile_dir}/[/]")
        shutil.copy2(pbf_source, pbf_copy)

    lua_profile = PROFILES[profile]

    common_docker_args = [
        "--platform",
        osrm_platform,
        "-v",
        f"{profile_dir}:/data",
        osrm_image,
    ]

    # Extract — check for .osrm.ebg (produced last) rather than .osrm
    # (produced early) so a partially-killed extract is properly re-run.
    ebg_file = osrm_base.with_suffix(".osrm.ebg")
    if not force and ebg_file.exists():
        console.print(f"  Extract already done for [cyan]{profile}[/], skipping.")
    else:
        extract_threads = threads
        while True:
            t_sub = time.monotonic()
            for stale in profile_dir.glob(f"{pbf_region}-latest.osrm*"):
                if stale.suffix != ".pbf":
                    stale.unlink(missing_ok=True)
            rc = _run_docker(
                [
                    *common_docker_args,
                    "osrm-extract",
                    "-t",
                    str(extract_threads),
                    "-p",
                    f"/opt/{lua_profile}.lua",
                    f"/data/{pbf_name}",
                ],
                label=f"Extracting ({profile}) with {extract_threads} thread(s)",
                verbose=verbose,
                allow_oom=True,
            )
            if rc == _OOM_EXIT_CODE and extract_threads > 1:
                extract_threads = max(1, extract_threads // 2)
                console.print(
                    f"\n  [bold yellow]OOM kill detected (exit 137).[/] "
                    f"Retrying [cyan]{profile}[/] extract with "
                    f"[bold]{extract_threads}[/] thread(s) to reduce peak memory.\n"
                )
                continue
            if rc == _OOM_EXIT_CODE:
                console.print(
                    Panel(
                        f"[bold red]Out of memory[/] during osrm-extract for "
                        f"[cyan]{profile}[/] even with 1 thread.\n\n"
                        "Increase Docker's memory allocation:\n"
                        "  [cyan]Docker Desktop[/]: Settings \u2192 Resources \u2192 Memory (\u226512 GB)\n"
                        "  [cyan]Colima[/]: colima stop && colima start --memory 16\n\n"
                        "Or build a native image to avoid Rosetta overhead:\n"
                        "  [cyan]make osrm-build[/]  (uses OSRM_IMAGE / OSRM_PLATFORM from .env)",
                        title="OOM — osrm-extract",
                        border_style="red",
                    )
                )
                raise typer.Exit(code=_OOM_EXIT_CODE)
            if rc != 0:
                raise typer.Exit(code=rc)
            break
        console.print(
            f"  [green]\u2192[/] Extract complete "
            f"({_fmt_elapsed(time.monotonic() - t_sub)})"
        )

    # Partition
    if not force and osrm_base.with_suffix(".osrm.partition").exists():
        console.print(f"  Partition already done for [cyan]{profile}[/], skipping.")
    else:
        t_sub = time.monotonic()
        _run_docker(
            [
                *common_docker_args,
                "osrm-partition",
                f"/data/{pbf_region}-latest.osrm",
            ],
            label=f"Partitioning ({profile})",
            verbose=verbose,
        )
        console.print(
            f"  [green]\u2192[/] Partition complete "
            f"({_fmt_elapsed(time.monotonic() - t_sub)})"
        )

    # Customise
    t_sub = time.monotonic()
    _run_docker(
        [
            *common_docker_args,
            "osrm-customize",
            f"/data/{pbf_region}-latest.osrm",
        ],
        label=f"Customising ({profile})",
        verbose=verbose,
    )
    console.print(
        f"  [green]\u2192[/] Customise complete "
        f"({_fmt_elapsed(time.monotonic() - t_sub)})"
    )

    if cleanup:
        console.print(f"  Removing PBF copy from [cyan]{profile_dir}/[/] (--cleanup)")
        pbf_copy.unlink(missing_ok=True)

    result.mark("completed", time.monotonic() - t0)
    return result


def _step_photon(*, force: bool, verbose: bool = False) -> StepResult:
    """Step 3 — download Photon European dataset.

    Uses the ``rtuszik/photon-docker`` container which has built-in resume
    support (download state persists on the mounted volume).  We monitor the
    host-side directory to provide a progress bar and parse container stdout
    for milestone messages.
    """
    result = StepResult("Photon dataset")
    t0 = time.monotonic()

    console.rule("[bold]Photon dataset (~60 GB)[/]")

    photon_data = DOCKER_DIR / "photon-data"
    photon_data.mkdir(parents=True, exist_ok=True)

    # The container considers the index present when this directory exists.
    node_dir = photon_data / "photon_data" / "node_1"
    temp_dir = photon_data / "temp"

    # -- State detection -------------------------------------------------------
    if not force and node_dir.is_dir():
        size_gb = _dir_size(photon_data) / (1024**3)
        console.print(
            f"  [green]Photon data already present[/] "
            f"([cyan]{size_gb:.1f} GB[/] at {node_dir}), skipping."
        )
        result.mark("skipped", time.monotonic() - t0)
        return result

    if temp_dir.is_dir() and any(temp_dir.iterdir()):
        existing_gb = _dir_size(temp_dir) / (1024**3)
        console.print(
            f"  [yellow]Partial download detected[/] ({existing_gb:.1f} GB in temp), "
            "container will resume."
        )
    else:
        console.print("  Starting fresh Photon download (~60 GB for europe).")

    # -- Run container with progress monitoring --------------------------------
    cmd = [
        "docker",
        "run",
        "--rm",
        "-e",
        "REGION=europe",
        "-e",
        "INITIAL_DOWNLOAD=TRUE",
        "-v",
        f"{photon_data}:/photon/data",
        "rtuszik/photon-docker:latest",
    ]

    tail: deque[str] = deque(maxlen=_TAIL_LINES)
    stop_event = threading.Event()

    _MILESTONES: dict[str, str] = {
        "Downloading": "Downloading Photon dataset\u2026",
        "Extracting": "Extracting search index\u2026",
        "erifying checksum": "Verifying checksum\u2026",
        "Moving": "Moving index into place\u2026",
        "health check": "Running health check\u2026",
        "Starting Photon": "Starting Photon server\u2026",
        "Sequential download process completed": "Download & extraction complete.",
    }
    seen_milestones: set[str] = set()

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.stdout is not None

    def _poll_size() -> None:
        """Background thread: update the progress bar with directory size."""
        while not stop_event.is_set():
            watched = temp_dir if temp_dir.is_dir() else photon_data
            size = _dir_size(watched)
            progress.update(size_task, completed=size)
            stop_event.wait(2.0)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        size_task = progress.add_task("Photon data", total=None)

        monitor = threading.Thread(target=_poll_size, daemon=True)
        monitor.start()

        for line in proc.stdout:
            stripped = line.rstrip()
            tail.append(stripped)

            for key, msg in _MILESTONES.items():
                if key in stripped and key not in seen_milestones:
                    seen_milestones.add(key)
                    progress.console.print(f"  [cyan]\u2192[/] {msg}")
                    break

            if verbose:
                progress.console.print(f"    {rich_escape(stripped)}")

        returncode = proc.wait()
        stop_event.set()
        monitor.join(timeout=5)

    if returncode != 0:
        console.print(
            f"[bold red]Photon container failed (exit {returncode}):[/]\n"
            f"  {shlex.join(cmd)}"
        )
        if tail:
            console.print("[dim]Last output lines:[/]")
            for ln in tail:
                console.print(f"  {rich_escape(ln)}")
        raise typer.Exit(code=returncode)

    for lock in photon_data.rglob("*.lock"):
        lock.unlink(missing_ok=True)
    console.print("  Removed stale OpenSearch lock files.")

    elapsed = time.monotonic() - t0
    size_gb = _dir_size(photon_data) / (1024**3)
    console.print(
        f"  [green]Photon data ready:[/] [cyan]{size_gb:.1f} GB[/] "
        f"in {_fmt_elapsed(elapsed)}"
    )
    console.print(
        "  For air-gap deployment, build a custom image \u2014 "
        "see [cyan]docker/photon/README.md[/]"
    )
    result.mark("completed", elapsed)
    return result


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


@app.command()
def prepare(
    cleanup: Annotated[
        bool,
        typer.Option(help="Delete PBF copies from OSRM profile dirs after processing."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option(help="Re-run all stages even if output files already exist."),
    ] = False,
    skip_nominatim: Annotated[
        bool,
        typer.Option(help="Skip the PBF download step for Nominatim."),
    ] = False,
    skip_osrm: Annotated[
        bool,
        typer.Option(help="Skip OSRM extract/partition/customise."),
    ] = False,
    skip_photon: Annotated[
        bool,
        typer.Option(help="Skip the Photon dataset download."),
    ] = False,
    threads: Annotated[
        int,
        typer.Option(
            help=(
                "Number of threads for osrm-extract (default 4). "
                "Use --threads 1 on machines with limited RAM (~6 GB Docker limit)."
            ),
        ),
    ] = 4,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v", help="Stream full Docker output instead of a spinner."
        ),
    ] = False,
) -> None:
    """Download and process geodata for Nominatim, OSRM, and Photon."""
    console.print(
        Panel(
            "[bold]airgap-geo-stack[/]  data preparation",
            subtitle="https://download.geofabrik.de",
            border_style="blue",
        )
    )

    _check_docker()

    pbf_region = os.environ.get("PBF_REGION", "great-britain")
    pbf_name = f"{pbf_region}-latest.osm.pbf"
    pbf_url = os.environ.get(
        "PBF_URL",
        f"https://download.geofabrik.de/europe/{pbf_name}",
    )
    osrm_image = os.environ.get("OSRM_IMAGE", "osrm/osrm-backend")
    osrm_platform = os.environ.get("OSRM_PLATFORM", "linux/amd64")

    results: list[StepResult] = []

    # Step 1 — PBF download
    pbf_dest = DOCKER_DIR / "nominatim" / "data" / pbf_name
    if not skip_nominatim or not skip_osrm:
        console.rule("[bold]Step 1: Download PBF[/]")
        try:
            results.append(
                _step_download_pbf(force=force, pbf_url=pbf_url, pbf_dest=pbf_dest)
            )
        except SystemExit:
            r = StepResult("Download PBF")
            r.mark("failed", 0.0)
            results.append(r)
    else:
        r = StepResult("Download PBF")
        r.mark("skipped", 0.0)
        results.append(r)

    # Step 2 — OSRM profiles
    if not skip_osrm:
        for profile in PROFILES:
            try:
                results.append(
                    _step_osrm_profile(
                        profile,
                        force=force,
                        cleanup=cleanup,
                        threads=threads,
                        pbf_name=pbf_name,
                        pbf_region=pbf_region,
                        pbf_source=pbf_dest,
                        osrm_image=osrm_image,
                        osrm_platform=osrm_platform,
                        verbose=verbose,
                    )
                )
            except SystemExit:
                r = StepResult(f"OSRM {profile}")
                r.mark("failed", 0.0)
                results.append(r)
    else:
        for profile in PROFILES:
            r = StepResult(f"OSRM {profile}")
            r.mark("skipped", 0.0)
            results.append(r)

    # Step 3 — Photon
    if not skip_photon:
        try:
            results.append(_step_photon(force=force, verbose=verbose))
        except SystemExit:
            r = StepResult("Photon dataset")
            r.mark("failed", 0.0)
            results.append(r)
    else:
        r = StepResult("Photon dataset")
        r.mark("skipped", 0.0)
        results.append(r)

    # Summary (always shown, even when steps failed)
    _print_summary(results)

    if any(r.status == "failed" for r in results):
        raise typer.Exit(code=1)


def _print_summary(results: list[StepResult]) -> None:
    """Print a Rich table summarising what happened."""
    table = Table(title="Preparation summary", show_lines=True)
    table.add_column("Step", style="bold")
    table.add_column("Status")
    table.add_column("Time", justify="right")

    status_style = {
        "completed": "[green]completed[/]",
        "skipped": "[yellow]skipped[/]",
        "failed": "[bold red]failed[/]",
        "pending": "[dim]pending[/]",
    }

    for r in results:
        elapsed = _fmt_elapsed(r.elapsed) if r.elapsed > 0 else "\u2014"
        table.add_row(r.name, status_style.get(r.status, r.status), elapsed)

    console.print()
    console.print(table)
    console.print()

    if any(r.status == "failed" for r in results):
        console.print("[bold red]Some steps failed \u2014 see output above.[/]")
    else:
        console.print("[bold green]Data preparation complete.[/]")

    console.print(
        "Start the stack with:\n"
        "  [cyan]cd docker && docker compose --env-file ../.env up -d[/]\n"
        "or\n"
        "  [cyan]cd .. && make up"
    )
