function barcodes_match(empty_message, length_message, mismatch_message) {
    var barcode = document.getElementById('id_barcode');
    var barcode_copy = document.getElementById('id_barcode_copy');

    if (barcode.value == barcode_copy.value) {
        barcode_copy.parentNode.setAttribute('class', 'has-success');
        return true;
    }
    barcode_copy.parentNode.setAttribute('class', 'has-error');

    if (barcode.value == "" || barcode_copy.value == "") {
        barcode.parentNode.setAttribute('class', 'has-error');
        alert(empty_message);
    } else if (barcode.value.length < 1) {
        barcode.parentNode.setAttribute('class', 'has-error');
        alert(length_message);
    }
    else {
        alert(mismatch_message);
    }

    return false;
}

function show_barcode_hide_placeholder() {
    $("#barcode_placeholder").hide();
    $("#id_barcode").show();
}

function hide_barcode_show_placeholder() {
    $("#barcode_placeholder").show();
    $("#id_barcode").hide();
}

$(document).ready(function() {
    $("#id_barcode").focusout(function(evt) {
        if ($('#id_barcode').val() != '' && $('#id_barcode_copy').val() != $('#id_barcode').val()) {
            hide_barcode_show_placeholder()
        }
    });

    $("#barcode_placeholder").focusin(function(evt) {
        show_barcode_hide_placeholder();
        $("#id_barcode").focus();
    });

    $("#id_barcode_copy").focusout(function(evt) {
        if ($("#id_barcode_copy").val().length == $("#id_barcode").val().length &&
                $('#id_barcode').val() != $("#id_barcode_copy").val()) {
            show_barcode_hide_placeholder();
        }
    });

    $("#id_barcode_copy").keyup(function(evt) {
        if ($("#id_barcode_copy").val().length == $("#id_barcode").val().length &&
                $("#id_barcode").val() == $("#id_barcode_copy").val()) {
            show_barcode_hide_placeholder();
            $("#id_barcode").parent().addClass('has-success');
            $("#id_barcode_copy").parent().addClass('has-success');
        } else if ($("#id_barcode_copy").val().length == $("#id_barcode").val().length) {
            show_barcode_hide_placeholder();
            $("#id_barcode").parent().addClass('has-error');
            $("#id_barcode_copy").parent().addClass('has-error');
        } else {
            hide_barcode_show_placeholder();
        }
    });

    $("#id_barcode_copy").focusin(function(evt) {
        hide_barcode_show_placeholder();
    });
});
