from datetime import datetime
import logging
from pathlib import Path
import zipfile

import click
import pandas as pd
from pyodk.client import Client
from pyodk.errors import PyODKError
from requests.exceptions import ConnectionError
from requests.exceptions import Timeout
from rich.console import Console
from rich.progress import Progress
from tenacity import before_sleep_log
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential


log = logging.getLogger(__name__)

console = Console()


CLI_HELP = "Export candidate results from ODK Central for a list of centers."

CLI_EPILOG = (
    "Setup:\n\n"
    "  1) Create a pyODK config file (default: .pyodk_config.toml).\n"
    "     https://getodk.github.io/pyodk/#configure\n\n"
    "Example:\n"
    "  uv run download-results --project-id=5 11034 11035 11036\n\n"
    "Output:\n"
    "  - candidate_results.csv: combined results across all centers\n"
    "  - media/: extracted images, filenames prefixed by center_id\n"
    "  - results_export_p<project_id>_<timestamp>.zip: upload bundle\n"
    "    (CSV + media/). Disable with --bundle=false."
)


@retry(
    retry=retry_if_exception_type((ConnectionError, Timeout)),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    before_sleep=before_sleep_log(log, logging.WARNING),
    reraise=True,
)
def export_form_submissions(
    client: Client,
    project_id: int,
    xml_form_id: str,
    dest_path: Path,
    attachments: bool = False,
):
    """
    Export form submissions to CSV archive
    https://docs.getodk.org/central-api-submission-management/#exporting-form-submissions-to-csv-via-post
    """
    url = f"/projects/{project_id}/forms/{xml_form_id}/submissions.csv.zip"
    console.log(f"Downloading {url}")
    response = client.get(
        url, params={"attachments": "false" if not attachments else "true"}
    )
    response.raise_for_status()
    dest_path.write_bytes(response.content)
    return response


def export_center_candidate_results(
    client: Client,
    project_id: int,
    center_ids: list[int],
    output_dir: Path,
) -> pd.DataFrame:
    """
    Download and parse candidate results for each center, returning a combined DataFrame.

    Intermediate ZIP files are saved under output_dir/<center_id>/results.zip.
    """
    IMAGE_COLUMNS = [
        "clerk_signature",
        "forms_picture_1st_page",
        "forms_picture_2nd_page",
    ]

    candidate_results: list[pd.DataFrame] = []
    media_dir = output_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    with Progress(console=console) as progress:
        task = progress.add_task("Exporting centers", total=len(center_ids))

        for center_id in center_ids:
            xml_form_id = f"results_{center_id}"
            center_dir = output_dir / str(center_id)
            center_dir.mkdir(parents=True, exist_ok=True)
            center_zip_path = center_dir / "results.zip"

            # Skip download if a valid ZIP already exists
            if center_zip_path.exists() and zipfile.is_zipfile(center_zip_path):
                console.log(f"Skipping {xml_form_id} (already downloaded)")
            else:
                export_form_submissions(
                    client=client,
                    project_id=project_id,
                    xml_form_id=xml_form_id,
                    dest_path=center_zip_path,
                    attachments=True,
                )
            # Extract data from the results CSVs contained within the ZIP archive
            with zipfile.ZipFile(center_zip_path, "r") as archive:
                # Candidate data
                candidates_path = Path(f"{xml_form_id}-candidate_results.csv")
                console.log(f"Extracting {candidates_path}")
                df = pd.read_csv(archive.open(str(candidates_path)))
                df["xml_form_id"] = xml_form_id
                df["center_id"] = center_id

                # Submission data
                submissions_path = Path(f"{xml_form_id}.csv")
                console.log(f"Extracting {submissions_path}")
                submissions_df = pd.read_csv(archive.open(str(submissions_path)))

                # Extract media files and prefix filenames with center_id
                media_names = [
                    n for n in archive.namelist() if n.startswith("media/")
                ]
                for name in media_names:
                    filename = Path(name).name
                    prefixed = f"{center_id}_{filename}"
                    dest = media_dir / prefixed
                    if not dest.exists():
                        dest.write_bytes(archive.read(name))
                console.log(f"Extracted {len(media_names)} media files")

                # Prefix image filenames in submissions before merge
                for col in IMAGE_COLUMNS:
                    if col in submissions_df.columns:
                        submissions_df[col] = submissions_df[col].apply(
                            lambda v, cid=center_id: f"{cid}_{v}"
                            if pd.notna(v) else v
                        )

                df = df.merge(
                    submissions_df[
                        [
                            "meta-instanceID",
                            "station_number",
                            "staff_user_name",
                            "ballot_number",
                            "race_type",
                        ]
                        + [c for c in IMAGE_COLUMNS if c in submissions_df.columns]
                    ],
                    left_on="PARENT_KEY",
                    right_on="meta-instanceID",
                    how="left",
                ).drop(columns=["meta-instanceID"])
                candidate_results.append(df)

            progress.advance(task)

    return pd.concat(candidate_results, ignore_index=True)


def create_upload_bundle(
    output_dir: Path,
    csv_path: Path,
    media_dir: Path,
    project_id: int,
) -> Path:
    """
    Package the candidate results CSV and media files into a timestamped ZIP
    for upload to the results system.

    The bundle is written to output_dir as results_export_p<project_id>_<timestamp>.zip
    with no compression (ZIP_STORED) since media is already compressed.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_path = output_dir / f"results_export_p{project_id}_{timestamp}.zip"

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_STORED) as zf:
        zf.write(csv_path, arcname=csv_path.name)
        if media_dir.exists():
            for media_file in sorted(media_dir.iterdir()):
                if media_file.is_file():
                    zf.write(media_file, arcname=f"media/{media_file.name}")

    return bundle_path


@click.command(help=CLI_HELP, epilog=CLI_EPILOG)
@click.option("--project-id", type=int, required=True, help="ODK Central project ID")
@click.argument("center-ids", type=click.INT, nargs=-1)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
    default=Path("results-output"),
    show_default=True,
    help="Directory for intermediate ZIP files and combined output CSV.",
)
@click.option(
    "--config",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path(".pyodk_config.toml"),
    show_default=True,
    help="Path to pyODK config file. See https://getodk.github.io/pyodk/#configure",
)
@click.option(
    "--bundle",
    type=bool,
    default=True,
    show_default=True,
    help=(
        "Create a timestamped ZIP bundle (candidate_results.csv + media/) in the "
        "output directory for upload to the results system. Pass --bundle=false to disable."
    ),
)
def main(
    project_id: int,
    center_ids: tuple[int, ...],
    output_dir: Path,
    config: Path,
    bundle: bool,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "candidate_results.csv"

    try:
        with Client(config_path=str(config)) as client:
            if not center_ids:
                forms = client.forms.list(project_id=project_id)
                center_ids = tuple(
                    int(f.xmlFormId.removeprefix("results_"))
                    for f in forms
                    if f.xmlFormId.startswith("results_")
                )
                console.log(f"Discovered {len(center_ids)} results forms")

            results_df = export_center_candidate_results(
                client=client,
                project_id=project_id,
                center_ids=list(center_ids),
                output_dir=output_dir,
            )
    except PyODKError as exc:
        raise click.ClickException(str(exc)) from exc

    results_df.to_csv(output_csv, index=False)
    console.log(f"Saved {len(results_df)} rows to {output_csv}")

    if bundle:
        bundle_path = create_upload_bundle(
            output_dir=output_dir,
            csv_path=output_csv,
            media_dir=output_dir / "media",
            project_id=project_id,
        )
        console.log(f"Created upload bundle: {bundle_path}")


if __name__ == "__main__":
    main()
