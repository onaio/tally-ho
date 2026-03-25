import zipfile
from pathlib import Path

import click
import pandas as pd
from pyodk.client import Client
from requests.exceptions import ConnectionError, Timeout
from rich.console import Console
from rich.progress import Progress
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

import logging

log = logging.getLogger(__name__)

console = Console()


CLI_HELP = "Export candidate results from ODK Central for a list of centers."

CLI_EPILOG = (
    "Setup:\n\n"
    "  1) Create a pyODK config file (default: .pyodk_config.toml).\n"
    "     https://getodk.github.io/pyodk/#configure\n\n"
    "Example:\n"
    "  uv run download-results-forms.py --project-id=5 11034 11035 11036"
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
    candidate_results: list[pd.DataFrame] = []

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
                df = df.merge(
                    submissions_df[
                        [
                            "meta-instanceID",
                            "station_number",
                            "staff_user_name",
                            "ballot_number",
                            "race_type",
                        ]
                    ],
                    left_on="PARENT_KEY",
                    right_on="meta-instanceID",
                    how="left",
                ).drop(columns=["meta-instanceID"])
                candidate_results.append(df)

            progress.advance(task)

    return pd.concat(candidate_results, ignore_index=True)


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
def main(project_id: int, center_ids: tuple[int, ...], output_dir: Path, config: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "candidate_results.csv"

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

    results_df.to_csv(output_csv, index=False)
    console.log(f"Saved {len(results_df)} rows to {output_csv}")


if __name__ == "__main__":
    main()
