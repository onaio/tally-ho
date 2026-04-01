import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from pyodk.errors import PyODKError

from src.download_results_forms import (
    export_center_candidate_results,
    export_form_submissions,
    main,
)


def make_test_zip(center_id, include_media=True):
    """Build an in-memory ZIP matching the ODK Central export layout."""
    form_id = f"results_{center_id}"

    candidates_csv = (
        "pos,candidate_id,candidate_name,candidate_result_round1,PARENT_KEY,KEY\n"
        f"1,101,Alice,25,uuid:abc-{center_id},uuid:abc-{center_id}/candidate_results[1]\n"
        f"2,102,Bob,30,uuid:abc-{center_id},uuid:abc-{center_id}/candidate_results[2]\n"
    )
    submissions_csv = (
        "meta-instanceID,station_number,staff_user_name,ballot_number,race_type,"
        "clerk_signature,forms_picture_1st_page,forms_picture_2nd_page\n"
        f"uuid:abc-{center_id},3,tester,1313,Individual,"
        f"sig_{center_id}.jpg,page1_{center_id}.jpg,\n"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{form_id}-candidate_results.csv", candidates_csv)
        zf.writestr(f"{form_id}.csv", submissions_csv)
        if include_media:
            zf.writestr(f"media/sig_{center_id}.jpg", b"fake-signature-jpg")
            zf.writestr(f"media/page1_{center_id}.jpg", b"fake-page1-jpg")
    return buf.getvalue()


@pytest.fixture()
def output_dir(tmp_path):
    return tmp_path / "output"


class TestExportFormSubmissions:
    def test_downloads_and_writes_zip(self, tmp_path):
        dest = tmp_path / "test.zip"
        zip_bytes = make_test_zip(999)

        mock_response = MagicMock()
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        export_form_submissions(
            client=mock_client,
            project_id=1,
            xml_form_id="results_999",
            dest_path=dest,
            attachments=True,
        )

        assert dest.exists()
        assert dest.read_bytes() == zip_bytes
        mock_client.get.assert_called_once_with(
            "/projects/1/forms/results_999/submissions.csv.zip",
            params={"attachments": "true"},
        )

    def test_passes_attachments_false(self, tmp_path):
        dest = tmp_path / "test.zip"

        mock_response = MagicMock()
        mock_response.content = b"fake"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        export_form_submissions(
            client=mock_client,
            project_id=1,
            xml_form_id="results_999",
            dest_path=dest,
            attachments=False,
        )

        mock_client.get.assert_called_once_with(
            "/projects/1/forms/results_999/submissions.csv.zip",
            params={"attachments": "false"},
        )


class TestExportCenterCandidateResults:
    def test_parses_and_merges_single_center(self, output_dir):
        center_id = 100
        zip_bytes = make_test_zip(center_id)

        mock_response = MagicMock()
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        df = export_center_candidate_results(
            client=mock_client,
            project_id=1,
            center_ids=[center_id],
            output_dir=output_dir,
        )

        assert len(df) == 2
        assert "station_number" in df.columns
        assert "staff_user_name" in df.columns
        assert "ballot_number" in df.columns
        assert "race_type" in df.columns
        assert "xml_form_id" in df.columns
        assert "center_id" in df.columns
        assert list(df["center_id"]) == [center_id, center_id]
        assert list(df["candidate_name"]) == ["Alice", "Bob"]
        # meta-instanceID should be dropped after merge
        assert "meta-instanceID" not in df.columns

    def test_combines_multiple_centers(self, output_dir):
        center_ids = [100, 200]

        def fake_get(url, params=None):
            for cid in center_ids:
                if str(cid) in url:
                    resp = MagicMock()
                    resp.content = make_test_zip(cid)
                    resp.raise_for_status = MagicMock()
                    return resp

        mock_client = MagicMock()
        mock_client.get.side_effect = fake_get

        df = export_center_candidate_results(
            client=mock_client,
            project_id=1,
            center_ids=center_ids,
            output_dir=output_dir,
        )

        assert len(df) == 4
        assert set(df["center_id"]) == {100, 200}

    def test_extracts_media_with_center_prefix(self, output_dir):
        center_id = 100
        zip_bytes = make_test_zip(center_id)

        mock_response = MagicMock()
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        export_center_candidate_results(
            client=mock_client,
            project_id=1,
            center_ids=[center_id],
            output_dir=output_dir,
        )

        media_dir = output_dir / "media"
        assert (media_dir / f"{center_id}_sig_{center_id}.jpg").exists()
        assert (media_dir / f"{center_id}_page1_{center_id}.jpg").exists()

    def test_image_columns_have_prefixed_filenames(self, output_dir):
        center_id = 100
        zip_bytes = make_test_zip(center_id)

        mock_response = MagicMock()
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        df = export_center_candidate_results(
            client=mock_client,
            project_id=1,
            center_ids=[center_id],
            output_dir=output_dir,
        )

        assert "clerk_signature" in df.columns
        assert "forms_picture_1st_page" in df.columns
        assert "forms_picture_2nd_page" in df.columns
        assert df["clerk_signature"].iloc[0] == f"{center_id}_sig_{center_id}.jpg"
        assert df["forms_picture_1st_page"].iloc[0] == f"{center_id}_page1_{center_id}.jpg"

    def test_skips_existing_valid_zip(self, output_dir):
        center_id = 100
        zip_bytes = make_test_zip(center_id)

        # Pre-populate the ZIP on disk
        center_dir = output_dir / str(center_id)
        center_dir.mkdir(parents=True)
        (center_dir / "results.zip").write_bytes(zip_bytes)

        mock_client = MagicMock()

        df = export_center_candidate_results(
            client=mock_client,
            project_id=1,
            center_ids=[center_id],
            output_dir=output_dir,
        )

        # Should not have called the API
        mock_client.get.assert_not_called()
        assert len(df) == 2


class TestCLI:
    def test_with_center_ids(self, output_dir):
        zip_bytes = make_test_zip(100)

        mock_response = MagicMock()
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        runner = CliRunner()
        with patch("src.download_results_forms.Client", return_value=mock_client):
            result = runner.invoke(
                main,
                ["--project-id=1", "--output-dir", str(output_dir), "100"],
            )

        assert result.exit_code == 0
        assert (output_dir / "candidate_results.csv").exists()

    def test_auto_discovers_centers(self, output_dir):
        zip_bytes = make_test_zip(100)

        mock_response = MagicMock()
        mock_response.content = zip_bytes
        mock_response.raise_for_status = MagicMock()

        mock_form = MagicMock()
        mock_form.xmlFormId = "results_100"
        other_form = MagicMock()
        other_form.xmlFormId = "polling_module_100"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.forms.list.return_value = [mock_form, other_form]
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        runner = CliRunner()
        with patch("src.download_results_forms.Client", return_value=mock_client):
            result = runner.invoke(
                main,
                ["--project-id=1", "--output-dir", str(output_dir)],
            )

        assert result.exit_code == 0
        mock_client.forms.list.assert_called_once_with(project_id=1)
        assert (output_dir / "candidate_results.csv").exists()

    def test_pyodk_error_exits_gracefully(self, output_dir):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.forms.list.side_effect = PyODKError("auth failed")

        runner = CliRunner()
        with patch("src.download_results_forms.Client", return_value=mock_client):
            result = runner.invoke(
                main,
                ["--project-id=1", "--output-dir", str(output_dir)],
            )

        assert result.exit_code == 1
        assert "auth failed" in result.output
