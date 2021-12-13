$(document).ready(function () {
    const downloadResults = function (data) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'form-results.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    $("#report").on("click", "#export-form-results", function () {
        $("#export-form-results").html("Exporting...");
        $("#export-form-results").prop("disabled", true);
        $.ajax({
            url: resultsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downloadResults(data);
                $("#export-form-results").removeAttr("disabled");
                $("#export-form-results").html("Export in JSON");
            },
        });
    });
});