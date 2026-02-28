"""Prepare all data required by the airgap-geo-stack Docker services.

Downloads an OSM PBF extract and processes it for Nominatim, OSRM (car, foot,
bike), and optionally downloads the Photon European geocoding dataset (~60 GB).

Set PBF_URL and PBF_REGION in your .env file to change the region.  Browse
https://download.geofabrik.de to find your extract.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Annotated

import httpx
import typer
from rich.console import Console
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
) -> None:
    """Run a ``docker run`` command, streaming output with a spinner."""
    cmd = ["docker", "run", "--rm", *args]
    with console.status(f"[bold cyan]{label}[/]") as status:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            status.update(f"[bold cyan]{label}[/]  {line.rstrip()}")
        returncode = proc.wait()

    if returncode != 0:
        console.print(
            f"[bold red]Command failed (exit {returncode}):[/] {' '.join(cmd)}"
        )
        raise typer.Exit(code=returncode)


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
        status: One of ``pending``, ``completed``, or ``skipped``.
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

    # Extract
    if not force and osrm_base.exists():
        console.print(f"  Extract already done for [cyan]{profile}[/], skipping.")
    else:
        _run_docker(
            [
                *common_docker_args,
                "osrm-extract",
                "-t",
                str(threads),
                "-p",
                f"/opt/{lua_profile}.lua",
                f"/data/{pbf_name}",
            ],
            label=f"Extracting ({profile}) with {threads} thread(s)",
        )

    # Partition
    if not force and osrm_base.with_suffix(".osrm.partition").exists():
        console.print(f"  Partition already done for [cyan]{profile}[/], skipping.")
    else:
        _run_docker(
            [
                *common_docker_args,
                "osrm-partition",
                f"/data/{pbf_region}-latest.osrm",
            ],
            label=f"Partitioning ({profile})",
        )

    # Customise
    _run_docker(
        [
            *common_docker_args,
            "osrm-customize",
            f"/data/{pbf_region}-latest.osrm",
        ],
        label=f"Customising ({profile})",
    )

    if cleanup:
        console.print(f"  Removing PBF copy from [cyan]{profile_dir}/[/] (--cleanup)")
        pbf_copy.unlink(missing_ok=True)

    result.mark("completed", time.monotonic() - t0)
    return result


def _step_photon(*, force: bool) -> StepResult:
    """Step 3 — download Photon European dataset."""
    result = StepResult("Photon dataset")
    t0 = time.monotonic()

    console.rule("[bold]Photon dataset (~60 GB)[/]")

    photon_data = DOCKER_DIR / "photon-data"
    photon_data.mkdir(parents=True, exist_ok=True)

    if not force and (photon_data / "search_index").is_dir():
        console.print(
            f"  Photon data already present at [cyan]{photon_data / 'search_index'}[/], "
            "skipping."
        )
        result.mark("skipped", time.monotonic() - t0)
        return result

    _run_docker(
        [
            "-e",
            "REGION=europe",
            "-e",
            "INITIAL_DOWNLOAD=TRUE",
            "-v",
            f"{photon_data}:/photon/data",
            "rtuszik/photon-docker:latest",
        ],
        label="Downloading Photon dataset",
    )

    console.print(f"  [green]Photon data downloaded to[/] {photon_data}/")
    console.print(
        "  For air-gap deployment, build a custom image — "
        "see [cyan]docker/photon/README.md[/]"
    )
    result.mark("completed", time.monotonic() - t0)
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
    if not skip_nominatim or not skip_osrm:
        console.rule("[bold]Step 1: Download PBF[/]")
        pbf_dest = DOCKER_DIR / "nominatim" / "data" / pbf_name
        results.append(
            _step_download_pbf(force=force, pbf_url=pbf_url, pbf_dest=pbf_dest)
        )
    else:
        r = StepResult("Download PBF")
        r.mark("skipped", 0.0)
        results.append(r)
        pbf_dest = DOCKER_DIR / "nominatim" / "data" / pbf_name

    # Step 2 — OSRM profiles
    if not skip_osrm:
        for profile in PROFILES:
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
                )
            )
    else:
        for profile in PROFILES:
            r = StepResult(f"OSRM {profile}")
            r.mark("skipped", 0.0)
            results.append(r)

    # Step 3 — Photon
    if not skip_photon:
        results.append(_step_photon(force=force))
    else:
        r = StepResult("Photon dataset")
        r.mark("skipped", 0.0)
        results.append(r)

    # Summary
    _print_summary(results)


def _print_summary(results: list[StepResult]) -> None:
    """Print a Rich table summarising what happened."""
    table = Table(title="Preparation summary", show_lines=True)
    table.add_column("Step", style="bold")
    table.add_column("Status")
    table.add_column("Time", justify="right")

    status_style = {
        "completed": "[green]completed[/]",
        "skipped": "[yellow]skipped[/]",
        "pending": "[dim]pending[/]",
    }

    for r in results:
        elapsed = f"{r.elapsed:.1f}s" if r.elapsed > 0 else "—"
        table.add_row(r.name, status_style.get(r.status, r.status), elapsed)

    console.print()
    console.print(table)
    console.print()
    console.print("[bold green]Data preparation complete.[/]")
    console.print(
        "Start the stack with:\n"
        "  [cyan]cd docker && docker compose --env-file ../.env up -d[/]"
    )
