$(document).ready(function () {
    const downLoadResultForms = function (data, fileName) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    $("#result-forms-report").on("click", "#export-result-forms", function () {
        $("#export-result-forms").html("Exporting...");
        $("#export-result-forms").prop("disabled", true);
        $.ajax({
            url: resultFormsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downLoadResultForms(data, `result_forms_${Date.now()}.json`);
                $("#export-result-forms").removeAttr("disabled");
                $("#export-result-forms").html("json");
            },
        });
    });

    $("#result-forms-report").on("click", "#export-result-forms-parlimentary", function () {
        $("#export-result-forms-parlimentary").html("Exporting...");
        $("#export-result-forms-parlimentary").prop("disabled", true);
        const parliamentaryRaceTypeNumbers = [0,1];
        $.ajax({
            url: resultFormsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                    race_types: parliamentaryRaceTypeNumbers
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downLoadResultForms(data, 'parliamentary_forms.json');
                $("#export-result-forms-parlimentary").removeAttr("disabled");
                $("#export-result-forms-parlimentary").html("Export Parliamentary Forms in JSON");
            },
        });
    });
});