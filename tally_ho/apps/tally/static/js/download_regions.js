$(document).ready(function () {
    const downLoadRegions = function (data) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'regions-list.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    $("#region-list-report").on("click", "#export-region-list", function () {
        $("#export-region-list").html("Exporting...");
        $("#export-region-list").prop("disabled", true);
        $.ajax({
            url: regionsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downLoadRegions(data);
                $("#export-region-list").removeAttr("disabled");
                $("#export-region-list").html("Export in JSON");
            },
        });
    });
});