$(document).ready(function () {
    const downLoadOffices = function (data) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'offices-list.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    $("#office-list-report").on("click", "#export-office-list", function () {
        $("#export-office-list").html("Exporting...");
        $("#export-office-list").prop("disabled", true);
        $.ajax({
            url: officesDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downLoadOffices(data);
                $("#export-office-list").removeAttr("disabled");
                $("#export-office-list").html("Export in JSON");
            },
        });
    });
});