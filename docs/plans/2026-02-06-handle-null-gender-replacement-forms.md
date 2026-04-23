# Handle Null Gender for Replacement Forms Import

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the result form import to handle null gender values on replacement forms (rows with empty center_code).

**Architecture:** The import logic at `import_result_forms.py:158` calls `.upper()` on the gender field value without checking for None. Replacement forms have empty gender fields, which is valid since the `ResultForm.gender` model field allows null. The fix is a null guard before calling `.upper()`.

**Tech Stack:** Django, DuckDB, Celery, pytest

**GitHub Issue:** <https://github.com/onaio/tally-ho/issues/550>

---

## Task 1: Create test fixture CSV with replacement forms

**Files:**

- Create: `tally_ho/libs/tests/fixtures/tally_setup_files/result_forms_with_replacements.csv`

### Step 1: Create the fixture file

Use the same dummy data pattern as the existing `result_forms.csv` fixture, and append two replacement form rows with empty center_code, station_number, gender, and name:

```csv
ballot_number,center_code,station_number,gender,name,office_name,barcode,serial_number,region_name
1,31001,2,female,Test School A,Tubruq,31001002001,,East
2,31001,2,female,Test School A,Tubruq,31001002002,,East
3,31001,2,female,Test School A,Tubruq,31001002003,,East
105,31001,2,female,Test School A,Tubruq,31001002105,,East
114,31001,2,female,Test School A,Tubruq,31001002114,,East
117,31001,2,female,Test School A,Tubruq,31001002117,,East
1,31001,1,male,Test School A,Tubruq,31001001001,,East
2,31001,1,male,Test School A,Tubruq,31001001002,,East
3,31001,1,male,Test School A,Tubruq,31001001003,,East
105,31001,1,male,Test School A,Tubruq,31001001105,,East
114,31001,1,male,Test School A,Tubruq,31001001114,,East
117,31001,1,male,Test School A,Tubruq,31001001117,,East
1,,,,,Tubruq,99990001001,,East
2,,,,,Tubruq,99990001002,,East
```

The last two rows are replacement forms with empty center_code, station_number, gender, and name.

### Step 2: Commit

```bash
git add tally_ho/libs/tests/fixtures/tally_setup_files/result_forms_with_replacements.csv
git commit -S -m "Add test fixture CSV with replacement form rows"
```

---

## Task 2: Write the failing test

**Files:**

- Modify: `tally_ho/apps/tally/tests/management/commands/test_async_import_result_form.py`

### Step 1: Add test method

Add a new test to `AsyncImportResultFormsTestCase` that imports result forms with replacement rows and verifies:

1. Import succeeds without error
2. Replacement forms are created with `is_replacement=True`
3. Replacement forms have `center=None` and `gender=None`

```python
def test_async_import_result_forms_with_replacements(self):
    csv_file_path = \
        str('tally_ho/libs/tests/fixtures/'
            'tally_setup_files/result_forms_with_replacements.csv')
    task = async_import_results_forms_from_result_forms_file.delay(
                    tally_id=self.tally.id,
                    csv_file_path=csv_file_path,)
    task.wait()

    result_forms = ResultForm.objects.filter(tally=self.tally)
    self.assertEqual(result_forms.count(), 14)

    replacement_forms = result_forms.filter(is_replacement=True)
    self.assertEqual(replacement_forms.count(), 2)

    for form in replacement_forms:
        self.assertIsNone(form.center)
        self.assertIsNone(form.gender)
        self.assertIsNone(form.station_number)
```

### Step 2: Run test to verify it fails

```bash
pytest tally_ho/apps/tally/tests/management/commands/test_async_import_result_form.py::AsyncImportResultFormsTestCase::test_async_import_result_forms_with_replacements -v
```

Expected: FAIL with `AttributeError: 'NoneType' object has no attribute 'upper'`

### Step 3: Commit

```bash
git add tally_ho/apps/tally/tests/management/commands/test_async_import_result_form.py
git commit -S -m "Add failing test for importing replacement forms with null gender"
```

---

## Task 3: Fix the null gender bug

**Files:**

- Modify: `tally_ho/apps/tally/management/commands/import_result_forms.py:157-159`

### Step 1: Add null guard

Change line 158 from:

```python
if field_name == 'gender':
    kwargs['gender'] = genders_by_name.get(field_val.upper())
    continue
```

To:

```python
if field_name == 'gender':
    kwargs['gender'] = \
        genders_by_name.get(field_val.upper()) \
        if field_val else None
    continue
```

### Step 2: Run the test to verify it passes

```bash
pytest tally_ho/apps/tally/tests/management/commands/test_async_import_result_form.py::AsyncImportResultFormsTestCase::test_async_import_result_forms_with_replacements -v
```

Expected: PASS

### Step 3: Run all import result form tests to check for regressions

```bash
pytest tally_ho/apps/tally/tests/management/commands/test_async_import_result_form.py -v
```

Expected: All tests PASS

### Step 4: Commit

```bash
git add tally_ho/apps/tally/management/commands/import_result_forms.py
git commit -S -m "Fix null gender crash when importing replacement forms

Closes #550"
```

---

## Task 4: Verify the full test suite passes

### Step 1: Run the full test suite

```bash
pytest --tb=short -q
```

Expected: All tests PASS

### Step 2: Fix any failures found, then commit
