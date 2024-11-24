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

    $("#in-report").on("click", "#export-results", function () {
        $("#export-results").html("Exporting...");
        $("#export-results").prop("disabled", true);
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
                downloadResults(data, `results_${Date.now()}.json`);
                $("#export-results").removeAttr("disabled");
                $("#export-results").html("All Results JSON Export");
            },
        });
    });

    $("#in-report").on("click", "#export-centers-by-mun-results", function () {
        $("#export-centers-by-mun-results").html("Exporting...");
        $("#export-centers-by-mun-results").prop("disabled", true);
        $.ajax({
            url: centersByMunResultsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downloadResults(data, `centers_by_mun_results_${Date.now()}.json`);
                $("#export-centers-by-mun-results").removeAttr("disabled");
                $("#export-centers-by-mun-results").html("All Centers By Mun Results JSON Export");
            },
        });
    });
    $("#in-report").on("click", "#export-centers-by-mun-c-votes-results", function () {
        $("#export-centers-by-mun-c-votes-results").html("Exporting...");
        $("#export-centers-by-mun-c-votes-results").prop("disabled", true);
        $.ajax({
            url: centersByMunCandidatesVotesResultsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downloadResults(data, `centers_by_mun_c_votes_results_${Date.now()}.json`);
                $("#export-centers-by-mun-c-votes-results").removeAttr("disabled");
                $("#export-centers-by-mun-c-votes-results").html("Centers By Mun Candidates Votes Results (JSON)");
            },
        });
    });
    $("#in-report").on("click", "#export-centers-stations-by-mun-c-votes-results", function () {
        $("#export-centers-stations-by-mun-c-votes-results").html("Exporting...");
        $("#export-centers-stations-by-mun-c-votes-results").prop("disabled", true);
        $.ajax({
            url: centersStationsByMunCandidatesVotesResultsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downloadResults(data, `centers_stations_by_mun_c_votes_results_${Date.now()}.json`);
                $("#export-centers-stations-by-mun-c-votes-results").removeAttr("disabled");
                $("#export-centers-stations-by-mun-c-votes-results").html("Centers/Stations By Mun Candidates Votes Results (JSON)");
            },
        });
    });

    $("#sub-cons-list-export").on("click", "#export-sub-cons", function () {
        $("#export-sub-cons").html("Exporting...");
        $("#export-sub-cons").prop("disabled", true);
        $.ajax({
            url: subConsDownloadUrl,
            data: {
                data: JSON.stringify({
                    tally_id: tallyId,
                }),
            },
            traditional: true,
            dataType: 'json',
            success: (data) => {
                downloadResults(data, `sub_cons_list_${Date.now()}.json`);
                $("#export-sub-cons").removeAttr("disabled");
                $("#export-sub-cons").html("json");
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