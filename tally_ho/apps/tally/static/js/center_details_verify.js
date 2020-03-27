function center_details_match(mismatch_message) {
    var center_number = document.getElementById("id_center_number");
    var center_number_copy = document.getElementById("id_center_number_copy");
    var station_number = document.getElementById("id_station_number");
    var station_number_copy = document.getElementById("id_station_number_copy");

    var valid = true;

    if (center_number.value === center_number_copy.value && center_number.value !== "" &&  center_number_copy.value !== "") {
        center_number.parentNode.setAttribute("class", "has-success");
        center_number_copy.parentNode.setAttribute("class", "has-success");
    } else {
        center_number.parentNode.setAttribute("class", "has-error");
        center_number_copy.parentNode.setAttribute("class", "has-error");
        valid = false;
    }

    if (station_number.value === station_number_copy.value && station_number.value !== "" &&  station_number_copy.value !== "") {
        station_number.parentNode.setAttribute("class", "has-success");
        station_number_copy.parentNode.setAttribute("class", "has-success");
    } else {
        station_number.parentNode.setAttribute("class", "has-error");
        station_number_copy.parentNode.setAttribute("class", "has-error");
        valid = false;
    }

    if (valid === false) {
        alert(mismatch_message);
    }

    return valid;
}

function show_center_number_hide_placeholder() {
    $("#center_number_placeholder").hide();
    $("#id_center_number").show();
}

function hide_center_number_show_placeholder() {
    $("#center_number_placeholder").show();
    $("#id_center_number").hide();
}

function show_station_number_hide_placeholder() {
    $("#station_number_placeholder").hide();
    $("#id_station_number").show();
}

function hide_station_number_show_placeholder() {
    $("#station_number_placeholder").show();
    $("#id_station_number").hide();
}

$(document).ready(function() {
    $("#id_center_number").focusout(function(evt) {
        if ($("#id_center_number").val() !== "" && $("#id_center_number_copy").val() !== $("#id_center_number").val()) {
            hide_center_number_show_placeholder()
        }
    });

    $("#center_number_placeholder").focusin(function(evt) {
        show_center_number_hide_placeholder();
        $("#id_center_number").focus();
    });

    $("#id_center_number_copy").focusout(function(evt) {
        if ($("#id_center_number_copy").val() !== "" && $("#id_center_number").val() !== $("#id_center_number_copy").val()) {
            show_center_number_hide_placeholder();
        }
    });

    $("#id_center_number_copy").keyup(function(evt) {
        if ($("#id_center_number_copy").val().length === 5 && $("#id_center_number").val() === $("#id_center_number_copy").val()) {
            show_center_number_hide_placeholder();
            $("#id_center_number").parent().addClass("has-success");
            $("#id_center_number_copy").parent().addClass("has-success");
        } else if ($("#id_center_number_copy").val().length === 5) {
            show_center_number_hide_placeholder();
            $("#id_center_number").parent().addClass("has-error");
            $("#id_center_number_copy").parent().addClass("has-error");
        } else {
            hide_center_number_show_placeholder();
        }
    });

    $("#id_center_number_copy").focusin(function(evt) {
        hide_center_number_show_placeholder();
    });


    $("#id_station_number").focusout(function(evt) {
        if ($("#id_station_number").val() !== "" && $("#id_station_number_copy").val() !== $("#id_station_number").val()) {
            hide_station_number_show_placeholder()
        }
    });

    $("#station_number_placeholder").focusin(function(evt) {
        show_station_number_hide_placeholder();
        $("#id_station_number").focus();
    });

    $("#d_station_number_copy").focusout(function(evt) {
        if ($("#id_station_number_copy").val() !== "" && $("#id_station_number").val() !== $("#id_station_number_copy").val()) {
            show_station_number_hide_placeholder();
        }
    });

    $("#id_station_number_copy").keyup(function(evt) {
            if ($("#id_station_number_copy").val().length > 0 && $("#id_station_number").val() === $("#id_station_number_copy").val()) {
            show_station_number_hide_placeholder();
            $("#id_station_number").parent().addClass("has-success");
            $("#id_station_number_copy").parent().addClass("has-success");
        } else {
            hide_station_number_show_placeholder();
        }
    });

    $("#id_station_number_copy").focusin(function(evt) {
        hide_station_number_show_placeholder();
    });
});
