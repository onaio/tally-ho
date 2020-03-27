var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

if (typeof csrftoken === 'undefined')
    csrftoken = getCookie("csrftoken");

var currentStep = 0;
var totalSteps = 5;

for (var i = 1; i <= totalSteps; i++) {
    var total = parseInt($("#total" + i).html());

    $("#progressbar" + i).progressbar({
        value: false,
        max: total
    });
}

$(document).ready(function() {
    currentStep = 1;
    doRequest();
});

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

function doRequest() {
    var elementsProcessed = parseInt($("#offset" + currentStep ).html());
    var total = parseInt($("#total" + currentStep).html());
    if (elementsProcessed < total) {
        $.ajax({
            url: $("#route").html(),
            //    timeout: 30000,
            type: "POST",
            data: {
                offset: $("#offset" + currentStep).html(),
                step: currentStep
            },
            success(data) {
                if (data.status === "OK") {
                    // If elements_processed is the same as offset, we didn"t
                    // process any new lines. Assume we are done and set the
                    // length to elements_processed.
                    if (data.elements_processed === 0) {
                        $("#total" + currentStep).html(elementsProcessed);
                    }
                    elementsProcessed += data.elements_processed;
                    $("#offset" + currentStep).html(elementsProcessed);
                    $("#progressbar" + currentStep).progressbar("option", "value", elementsProcessed);
                    doRequest();
                }
            }
        });
    }
    else {
        if (currentStep < totalSteps) {
            currentStep += 1;
            doRequest();
        }
        else {
            location.href = $("#route_destination").html();
        }
    }
}
