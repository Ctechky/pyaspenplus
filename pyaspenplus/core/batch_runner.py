"""Command-line batch runner for Aspen Plus simulations.

Runs Aspen Plus via its command-line interface (``AspenPlus.exe``) using
:mod:`subprocess`, bypassing COM automation entirely.  This requires
Aspen Plus to be *installed* but does not need a COM server or interactive
GUI session.

Workflow::

    runner = BatchRunner()                    # auto-detect exe
    result = runner.run("model.bkp")          # run & wait
    print(result.return_code, result.elapsed)

Combined with :class:`BKPWriter`, this enables a full modify-run-read
cycle without COM::

    from pyaspenplus.core.bkp_writer import BKPWriter
    from pyaspenplus.core.bkp_parser import BKPParser
    from pyaspenplus.core.batch_runner import BatchRunner

    writer = BKPWriter("model.bkp")
    writer.set_stream_temp("FEED", 550.0)
    modified = writer.save("model_run.bkp")

    runner = BatchRunner()
    result = runner.run(modified)

    parser = BKPParser(modified)
    data = parser.parse()
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyaspenplus.utils.logger import get_logger

log = get_logger("batch_runner")


class BatchRunnerError(Exception):
    """Raised when a batch run operation fails."""


# ------------------------------------------------------------------
# Common Aspen Plus install locations (newest first)
# ------------------------------------------------------------------
_CANDIDATE_DIRS = [
    r"C:\Program Files\AspenTech\Aspen Plus V14.0\GUI\Xeq",
    r"C:\Program Files\AspenTech\Aspen Plus V13.0\GUI\Xeq",
    r"C:\Program Files\AspenTech\Aspen Plus V12.1\GUI\Xeq",
    r"C:\Program Files\AspenTech\Aspen Plus V12.0\GUI\Xeq",
    r"C:\Program Files\AspenTech\Aspen Plus V11.0\GUI\Xeq",
    r"C:\Program Files\AspenTech\Aspen Plus V10.0\GUI\Xeq",
    r"C:\Program Files (x86)\AspenTech\Aspen Plus V14.0\GUI\Xeq",
    r"C:\Program Files (x86)\AspenTech\Aspen Plus V13.0\GUI\Xeq",
    r"C:\Program Files (x86)\AspenTech\Aspen Plus V12.1\GUI\Xeq",
    r"C:\Program Files (x86)\AspenTech\Aspen Plus V12.0\GUI\Xeq",
    r"C:\Program Files (x86)\AspenTech\Aspen Plus V11.0\GUI\Xeq",
    r"C:\Program Files (x86)\AspenTech\Aspen Plus V10.0\GUI\Xeq",
]

_ASPEN_EXE_NAMES = ["AspenPlus.exe", "apmain.exe", "APMainUI.exe"]


def find_aspen_executable() -> Path | None:
    """Search common paths for the Aspen Plus executable.

    Also checks ``ASPENPLUS_EXE`` environment variable and ``PATH``.
    """
    env = os.environ.get("ASPENPLUS_EXE")
    if env:
        p = Path(env)
        if p.is_file():
            return p

    for d in _CANDIDATE_DIRS:
        dp = Path(d)
        if dp.is_dir():
            for name in _ASPEN_EXE_NAMES:
                exe = dp / name
                if exe.is_file():
                    return exe

    import shutil as _shutil
    for name in _ASPEN_EXE_NAMES:
        found = _shutil.which(name)
        if found:
            return Path(found)

    return None


# ------------------------------------------------------------------
# Run result
# ------------------------------------------------------------------

@dataclass
class BatchRunResult:
    """Result of a batch Aspen Plus run."""

    input_file: Path = field(default_factory=lambda: Path("."))
    output_file: Path | None = None
    return_code: int = -1
    elapsed_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    success: bool = False

    def summary(self) -> str:
        status = "SUCCESS" if self.success else f"FAILED (rc={self.return_code})"
        lines = [
            f"Batch run: {status}",
            f"  Input:   {self.input_file}",
            f"  Output:  {self.output_file or 'N/A'}",
            f"  Elapsed: {self.elapsed_seconds:.1f}s",
        ]
        if self.stderr.strip():
            lines.append(f"  Stderr:  {self.stderr[:200]}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------

class BatchRunner:
    """Run Aspen Plus simulations via the command line.

    Parameters
    ----------
    exe_path : str | Path | None
        Explicit path to the Aspen Plus executable.
        If ``None``, auto-detection is attempted.
    timeout : int
        Maximum seconds to wait for the simulation to finish.
    """

    def __init__(
        self,
        exe_path: str | Path | None = None,
        *,
        timeout: int = 3600,
    ) -> None:
        if exe_path is not None:
            self._exe = Path(exe_path).resolve()
            if not self._exe.is_file():
                raise BatchRunnerError(f"Executable not found: {self._exe}")
        else:
            self._exe = find_aspen_executable()
        self._timeout = timeout

    @property
    def exe_path(self) -> Path | None:
        return self._exe

    @property
    def is_available(self) -> bool:
        """``True`` if an Aspen Plus executable was found."""
        return self._exe is not None

    def run(
        self,
        filepath: str | Path,
        *,
        output_dir: str | Path | None = None,
        extra_args: list[str] | None = None,
        timeout: int | None = None,
    ) -> BatchRunResult:
        """Run an Aspen Plus simulation in batch mode.

        Parameters
        ----------
        filepath : str | Path
            Path to ``.bkp`` or ``.apw`` input file.
        output_dir : str | Path | None
            Directory for output files.  Defaults to the input file's directory.
        extra_args : list[str] | None
            Additional command-line arguments.
        timeout : int | None
            Override the default timeout (seconds).

        Returns
        -------
        BatchRunResult
        """
        if self._exe is None:
            raise BatchRunnerError(
                "Aspen Plus executable not found. "
                "Set ASPENPLUS_EXE environment variable or pass exe_path."
            )

        infile = Path(filepath).resolve()
        if not infile.exists():
            raise FileNotFoundError(f"Input file not found: {infile}")

        out_dir = Path(output_dir).resolve() if output_dir else infile.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [str(self._exe), "/f", str(infile), "/r"]

        if output_dir:
            cmd.extend(["/o", str(out_dir)])
        if extra_args:
            cmd.extend(extra_args)

        log.info("Running: %s", " ".join(cmd))
        t0 = time.monotonic()

        result = BatchRunResult(input_file=infile)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self._timeout,
                cwd=str(infile.parent),
            )
            result.return_code = proc.returncode
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = proc.returncode == 0
        except subprocess.TimeoutExpired:
            result.stderr = f"Timed out after {timeout or self._timeout}s"
            log.error("Batch run timed out for %s", infile)
        except Exception as exc:
            result.stderr = str(exc)
            log.error("Batch run failed: %s", exc)

        result.elapsed_seconds = time.monotonic() - t0

        bkp_out = infile.with_suffix(".bkp")
        if bkp_out.is_file():
            result.output_file = bkp_out

        log.info(
            "Batch run finished: rc=%d, elapsed=%.1fs",
            result.return_code, result.elapsed_seconds,
        )
        return result

    def run_and_parse(
        self,
        filepath: str | Path,
        **run_kwargs: Any,
    ) -> tuple["BatchRunResult", Any]:
        """Run a simulation and parse the output BKP.

        Returns ``(run_result, parse_result)`` where *parse_result* is a
        :class:`~pyaspenplus.core.bkp_parser.BKPParseResult` (or ``None``
        if the run failed).
        """
        from pyaspenplus.core.bkp_parser import BKPParser

        run_result = self.run(filepath, **run_kwargs)

        parse_result = None
        if run_result.success and run_result.output_file:
            try:
                parser = BKPParser(run_result.output_file)
                parse_result = parser.parse()
            except Exception as exc:
                log.warning("Failed to parse output: %s", exc)

        return run_result, parse_result
