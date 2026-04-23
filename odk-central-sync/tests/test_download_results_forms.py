import io
import re
from unittest.mock import MagicMock
from unittest.mock import patch
import zipfile

from click.testing import CliRunner
from pyodk.errors import PyODKError
import pytest

from src.download_results_forms import create_upload_bundle
from src.download_results_forms import export_center_candidate_results
from src.download_results_forms import export_form_submissions
from src.download_results_forms import main


def make_test_zip(center_id, include_media=True):
    """Build an in-memory ZIP matching the ODK Central export layout."""
    form_id = f"results_{center_id}"

    candidates_csv = (
        "pos,candidate_id,candidate_name,"
        "candidate_result_round1,candidate_result_r2-candidate_result_round2,"
        "PARENT_KEY,KEY\n"
        f"1,101,Alice,25,26,uuid:abc-{center_id},"
        f"uuid:abc-{center_id}/candidate_results[1]\n"
        f"2,102,Bob,30,31,uuid:abc-{center_id},"
        f"uuid:abc-{center_id}/candidate_results[2]\n"
    )
    submissions_csv = (
        "meta-instanceID,station_number,staff_user_name,ballot_number,race_type,"
        "intro-barcode,"
        "reconciliation_r1-number_ballots_received_r1,"
        "reconciliation_r1-number_voter_cards_r1,"
        "reconciliation_r1-number_valid_ballots_r1,"
        "reconciliation_r1-number_invalid_ballots_r1,"
        "reconciliation_r1-number_ballots_inside_box_r1,"
        "reconciliation_r2-number_ballots_received_r2,"
        "reconciliation_r2-number_voter_cards_r2,"
        "reconciliation_r2-number_valid_ballots_r2,"
        "reconciliation_r2-number_invalid_ballots_r2,"
        "reconciliation_r2-number_ballots_inside_box_r2,"
        "clerk_signature,forms_picture_1st_page,forms_picture_2nd_page\n"
        f"uuid:abc-{center_id},3,tester,1313,Individual,"
        f"{center_id}003001,"
        "200,150,140,10,150,"
        "204,149,139,10,149,"
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

    def test_extracts_barcode(self, output_dir):
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

        assert "barcode" in df.columns
        assert list(df["barcode"]) == [f"{center_id}003001"] * 2
        # Original intro-barcode should have been renamed
        assert "intro-barcode" not in df.columns

    def test_extracts_round2_candidate_votes(self, output_dir):
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

        assert "candidate_result_round2" in df.columns
        assert list(df["candidate_result_round2"]) == [26, 31]
        # Original hyphenated column should have been renamed away
        assert (
            "candidate_result_r2-candidate_result_round2" not in df.columns
        )
        # Round 1 should still be present unchanged
        assert "candidate_result_round1" in df.columns
        assert list(df["candidate_result_round1"]) == [25, 30]

    def test_extracts_reconciliation_fields(self, output_dir):
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

        r1_cols = [
            "reconciliation_r1-number_ballots_received_r1",
            "reconciliation_r1-number_voter_cards_r1",
            "reconciliation_r1-number_valid_ballots_r1",
            "reconciliation_r1-number_invalid_ballots_r1",
            "reconciliation_r1-number_ballots_inside_box_r1",
        ]
        r2_cols = [
            "reconciliation_r2-number_ballots_received_r2",
            "reconciliation_r2-number_voter_cards_r2",
            "reconciliation_r2-number_valid_ballots_r2",
            "reconciliation_r2-number_invalid_ballots_r2",
            "reconciliation_r2-number_ballots_inside_box_r2",
        ]
        for col in r1_cols + r2_cols:
            assert col in df.columns, f"missing reconciliation column: {col}"

        # Spot-check the values round-trip correctly
        assert (
            df["reconciliation_r1-number_ballots_received_r1"].iloc[0] == 200
        )
        assert df["reconciliation_r1-number_valid_ballots_r1"].iloc[0] == 140
        assert (
            df["reconciliation_r2-number_ballots_received_r2"].iloc[0] == 204
        )
        assert df["reconciliation_r2-number_valid_ballots_r2"].iloc[0] == 139

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


class TestCreateUploadBundle:
    def test_bundle_contains_csv_and_media(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        csv_path = output_dir / "candidate_results.csv"
        csv_path.write_text("a,b\n1,2\n")
        media_dir = output_dir / "media"
        media_dir.mkdir()
        (media_dir / "100_sig.jpg").write_bytes(b"img1")
        (media_dir / "100_page.jpg").write_bytes(b"img2")

        bundle_path = create_upload_bundle(
            output_dir=output_dir,
            csv_path=csv_path,
            media_dir=media_dir,
            project_id=14,
        )

        assert bundle_path.exists()
        assert bundle_path.parent == output_dir
        with zipfile.ZipFile(bundle_path) as zf:
            names = set(zf.namelist())
            assert "candidate_results.csv" in names
            assert "media/100_sig.jpg" in names
            assert "media/100_page.jpg" in names
            # ZIP_STORED = no compression
            for info in zf.infolist():
                assert info.compress_type == zipfile.ZIP_STORED

    def test_bundle_filename_has_project_id_and_timestamp(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        csv_path = output_dir / "candidate_results.csv"
        csv_path.write_text("a,b\n1,2\n")

        bundle_path = create_upload_bundle(
            output_dir=output_dir,
            csv_path=csv_path,
            media_dir=output_dir / "media",
            project_id=42,
        )

        assert re.fullmatch(
            r"results_export_p42_\d{8}_\d{6}\.zip", bundle_path.name
        )

    def test_bundle_handles_missing_media_dir(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        csv_path = output_dir / "candidate_results.csv"
        csv_path.write_text("a,b\n1,2\n")

        bundle_path = create_upload_bundle(
            output_dir=output_dir,
            csv_path=csv_path,
            media_dir=output_dir / "media",
            project_id=1,
        )

        assert bundle_path.exists()
        with zipfile.ZipFile(bundle_path) as zf:
            names = set(zf.namelist())
            assert names == {"candidate_results.csv"}

    def test_bundle_handles_empty_media_dir(self, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        csv_path = output_dir / "candidate_results.csv"
        csv_path.write_text("a,b\n1,2\n")
        media_dir = output_dir / "media"
        media_dir.mkdir()

        bundle_path = create_upload_bundle(
            output_dir=output_dir,
            csv_path=csv_path,
            media_dir=media_dir,
            project_id=1,
        )

        with zipfile.ZipFile(bundle_path) as zf:
            assert set(zf.namelist()) == {"candidate_results.csv"}


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

    def test_creates_bundle_by_default(self, output_dir):
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
                ["--project-id=14", "--output-dir", str(output_dir), "100"],
            )

        assert result.exit_code == 0
        bundles = list(output_dir.glob("results_export_p14_*.zip"))
        assert len(bundles) == 1

    def test_bundle_false_skips_bundle(self, output_dir):
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
                [
                    "--project-id=14",
                    "--output-dir",
                    str(output_dir),
                    "--bundle=false",
                    "100",
                ],
            )

        assert result.exit_code == 0
        assert (output_dir / "candidate_results.csv").exists()
        bundles = list(output_dir.glob("results_export_p*.zip"))
        assert len(bundles) == 0

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
