$(document).ready(function () {
    const downLoadCandidates = function (data) {
        const url = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `candidates_list_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
    };

    $("#candidates-list-report").on("click", "#export-candidates-list", function () {
        $("#export-candidates-list").html("Exporting...");
        $("#export-candidates-list").prop("disabled", true);
        $.ajax({
            url: candidatesDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downLoadCandidates(data);
                $("#export-candidates-list").removeAttr("disabled");
                $("#export-candidates-list").html("json");
            },
        });
    });
});