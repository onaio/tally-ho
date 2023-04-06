$(document).ready(function () {
    const downloadResults = function (data, fileName) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    $("#report").on("click", "#export-form-results-presidential", function () {
        $("#export-form-results-presidential").html("Exporting...");
        $("#export-form-results-presidential").prop("disabled", true);
        const presidentialRaceTypeNumber = [5];
        $.ajax({
            url: resultsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                    race_types: presidentialRaceTypeNumber
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downloadResults(data, 'presidential_results.json');
                $("#export-form-results-presidential").removeAttr("disabled");
                $("#export-form-results-presidential").html("Export Presidential Results in JSON");
            },
        });
    });

    $("#report").on("click", "#export-form-results-parliamentary", function () {
        $("#export-form-results-parliamentary").html("Exporting...");
        $("#export-form-results-parliamentary").prop("disabled", true);
        const parliamentaryRaceTypeNumbers = [0,1];
        $.ajax({
            url: resultsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                    race_types: parliamentaryRaceTypeNumbers
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downloadResults(data, 'parliamentary_results.json');
                $("#export-form-results-parliamentary").removeAttr("disabled");
                $("#export-form-results-parliamentary").html("Export Parliamentary Results in JSON");
            },
        });
    });
});