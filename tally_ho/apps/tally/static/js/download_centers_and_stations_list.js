$(document).ready(function () {
    const downLoadCentersAndStations = function (data) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = 'centers-and-stations-list.json';
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    $("#centers-and-stations-list-report").on("click", "#export-centers-and-stations-list", function () {
        $("#export-centers-and-stations-list").html("Exporting...");
        $("#export-centers-and-stations-list").prop("disabled", true);
        $.ajax({
            url: centersAndStationsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downLoadCentersAndStations(data);
                $("#export-centers-and-stations-list").removeAttr("disabled");
                $("#export-centers-and-stations-list").html("Export in JSON");
            },
        });
    });
});