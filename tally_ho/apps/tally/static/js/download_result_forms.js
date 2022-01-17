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

    $("#result-forms-report").on("click", "#export-result-forms-presidential", function () {
        $("#export-result-forms-presidential").html("Exporting...");
        $("#export-result-forms-presidential").prop("disabled", true);
        const presidentialRaceTypeNumber = [5];
        $.ajax({
            url: resultFormsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                    race_types: presidentialRaceTypeNumber
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downLoadResultForms(data, 'presidential_forms.json');
                $("#export-result-forms-presidential").removeAttr("disabled");
                $("#export-result-forms-presidential").html("Export Presidential Forms in JSON");
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