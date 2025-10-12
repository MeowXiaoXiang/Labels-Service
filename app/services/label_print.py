# app/services/label_print.py
# Label Print Service (Core Business Logic)
# - JSON → CSV → gLabels → PDF
# - info logs: job success/failure
# - debug logs: job start, CSV writing, temp file cleanup

from __future__ import annotations

import csv
import os
import re
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from loguru import logger

from app.utils.glabels_engine import GlabelsEngine, GlabelsRunError


# Utility functions
def _collect_fieldnames(rows: List[Dict], exclude: Iterable[str] = ()) -> List[str]:
    """
    Collect field names from JSON rows in the order of appearance.
    Optionally exclude specific keys.
    """
    seen = set()
    order: List[str] = []
    for row in rows:
        for k in row.keys():
            if k in exclude:
                continue
            if k not in seen:
                seen.add(k)
                order.append(k)
    return order


def _slug(s: str) -> str:
    """
    Convert string to a safe filename.
    Allowed characters: A-Z, a-z, 0-9, dot, underscore, hyphen.
    """
    return re.sub(r"[^A-Za-z0-9._-]", "_", s or "")


# Label Print Service
class LabelPrintService:
    def __init__(
        self,
        max_parallel: Optional[int] = None,
        default_timeout: int = 300,
        keep_csv: bool = False,
    ):
        if max_parallel is None:
            max_parallel = max(1, (os.cpu_count() or 2) - 1)

        self.keep_csv = keep_csv
        self.engine = GlabelsEngine(
            max_parallel=max_parallel,
            default_timeout=default_timeout,
        )

    # --------------------------------------------------------
    # Generate output filename
    # --------------------------------------------------------
    @staticmethod
    def make_output_filename(template_name: str) -> str:
        """
        Generate a safe output PDF filename based on template name + timestamp.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(template_name).stem
        return f"{_slug(base)}_{ts}.pdf"

    # --------------------------------------------------------
    # JSON → CSV
    # --------------------------------------------------------
    def _json_to_csv(
        self,
        data: List[Dict],
        csv_path: Path,
        field_order: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Write JSON rows into a CSV file.
        """
        if not data:
            raise ValueError("No label data to generate CSV")

        fieldnames = field_order or _collect_fieldnames(data)
        logger.debug(f"[LabelPrint] Writing CSV {csv_path}, fields={fieldnames}")

        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

        return fieldnames

    # --------------------------------------------------------
    # Resolve template path
    # --------------------------------------------------------
    def _resolve_template(self, template_name: str) -> Path:
        """
        Verify template file exists inside the templates/ directory.
        """
        if not template_name.lower().endswith(".glabels"):
            raise ValueError("Only .glabels templates are allowed")

        lower_name = template_name.lower()
        for f in Path("templates").iterdir():
            if f.name.lower() == lower_name:
                return f

        raise FileNotFoundError(f"gLabels template not found: {template_name}")

    # --------------------------------------------------------
    # Core method: Generate PDF
    # --------------------------------------------------------
    async def generate_pdf(
        self,
        *,
        job_id: str,
        template_name: str,
        data: List[Dict],
        copies: int = 1,
        filename: str,
        field_order: Optional[List[str]] = None,
    ) -> Path:
        """
        Generate PDF based on template and JSON data.
        Steps:
        - Convert JSON → temp CSV
        - Call glabels-3-batch
        - Save PDF into output/
        """
        template_path = self._resolve_template(template_name)

        # Ensure output directory exists
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Prepare output PDF
        output_pdf = output_dir / filename

        # Handle CSV creation based on keep_csv setting
        if self.keep_csv:
            # Keep CSV: save to temp/ directory with job_id name
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            csv_path = temp_dir / f"{job_id}.csv"
            # JSON → CSV
            self._json_to_csv(data, csv_path, field_order=field_order)
        else:
            # Don't keep CSV: use tempfile, let system auto-cleanup
            temp_csv_fd, temp_csv_name = tempfile.mkstemp(
                suffix=".csv", prefix=f"labels_{job_id}_"
            )
            csv_path = Path(temp_csv_name)
            os.close(temp_csv_fd)  # Close file descriptor, we'll use Path to write
            # JSON → CSV
            self._json_to_csv(data, csv_path, field_order=field_order)

        # Run glabels
        start_time = time.time()
        logger.debug(
            f"[LabelPrint] 🚀 START job_id={job_id}, template={template_path}, copies={copies}"
        )

        try:
            await self.engine.run_batch(
                output_pdf=output_pdf,
                template_path=template_path,
                csv_path=csv_path,
                extra_args=[f"--copies={copies}"] if copies > 1 else [],
            )
            duration = time.time() - start_time
            logger.info(
                f"[LabelPrint] ✅ job_id={job_id} finished in {duration:.2f}s → {output_pdf}"
            )
        except GlabelsRunError as e:
            duration = time.time() - start_time
            logger.error(
                f"[LabelPrint] ❌ job_id={job_id} failed after {duration:.2f}s "
                f"(rc={e.returncode})\n{e.stderr}"
            )
            truncated_stderr = (
                (e.stderr[:1024] + "...") if len(e.stderr) > 1024 else e.stderr
            )
            raise RuntimeError(
                f"Label PDF generation failed (rc={e.returncode})\n{truncated_stderr}"
            ) from e
        finally:
            # Cleanup: only needed for keep_csv=False with tempfile
            if not self.keep_csv and csv_path.exists():
                try:
                    csv_path.unlink()
                    logger.debug(f"[LabelPrint] 🗑️ Deleted temp CSV: {csv_path}")
                except OSError:
                    logger.warning(f"[LabelPrint] ⚠️ Cannot delete temp CSV: {csv_path}")
            elif self.keep_csv:
                logger.debug(f"[LabelPrint] 📁 Kept CSV file: {csv_path}")

        return output_pdf
