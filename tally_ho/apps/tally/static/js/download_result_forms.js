$(document).ready(function () {
    const downLoadResultForms = function (data) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'result-forms.json';
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
                downLoadResultForms(data);
                $("#export-result-forms").removeAttr("disabled");
                $("#export-result-forms").html("Export in JSON");
            },
        });
    });
});