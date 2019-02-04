function barcodes_match(empty_message, length_message, mismatch_message) {
    const barcode = document.getElementById('id_barcode');
    const barcode_copy = document.getElementById('id_barcode_copy');
    const barcode_scan_entry = document.getElementById('barcode_scan_entry').hidden;
    if (barcode_scan_entry){
        if (barcode.value === barcode_copy.value) {
            barcode_copy.parentNode.setAttribute('class', 'has-success');
            return true;
        }
        barcode_copy.parentNode.setAttribute('class', 'has-error');

        if (barcode.value === "" || barcode_copy.value === "") {
            barcode.parentNode.setAttribute('class', 'has-error');
            alert(empty_message);
        } else if (barcode.value.length < 1) {
            barcode.parentNode.setAttribute('class', 'has-error');
            alert(length_message);
        }
        else {
            alert(mismatch_message);
        }
    }

    return;
}

let barcode_number = '';

const barcode_scanner = (barcode_input_field) => {
    if (barcode_input_field) {
        barcode_input_field.addEventListener('keydown', function (e) {
            e.preventDefault();
            let textInput = e.key
            if (textInput.length === 1 || (e.keyCode === 13)) {
                if (!(isNaN(parseInt(textInput))) && e.code === 'KeyA') {
                    barcode_number = barcode_number + textInput;
                }
                if (barcode_number && (e.keyCode === 13)) {
                    barcode_input_field.value = barcode_number;
                    barcode_input_field.readOnly = true;
                }
            }

        });
    }
}

document.onreadystatechange = function () {
    if (document.readyState === "interactive") {
        const barcode_scan_input_field = document.getElementById('id_scanned_barcode');
        barcode_scan_input_field.value = '';
    }
    else if (document.readyState === "complete") {
        const barcode_scan_input_field = document.getElementById('id_scanned_barcode');
        const barcode_manual_entry_input_field = document.getElementById('id_barcode');
        const barcode_copy_manual_entry_input_field = document.getElementById('id_barcode_copy');
        barcode_number = '';
        barcode_scan_input_field.setAttribute('required', 'true');
        barcode_manual_entry_input_field.removeAttribute('required');
        barcode_copy_manual_entry_input_field.removeAttribute('required');
        barcode_scanner(barcode_scan_input_field)
    }
}


function show_barcode_hide_placeholder() {
    $("#barcode_placeholder").hide();
    $("#id_barcode").show();
}

function hide_barcode_show_placeholder() {
    $("#barcode_placeholder").show();
    $("#id_barcode").hide();
}

const input_validation = () => $(document).ready(function () {
    $("#id_barcode").focusout(function (evt) {
        if ($('#id_barcode').val() != '' && $('#id_barcode_copy').val() != $('#id_barcode').val()) {
            hide_barcode_show_placeholder()
        }
    });

    $("#barcode_placeholder").focusin(function (evt) {
        show_barcode_hide_placeholder();
        $("#id_barcode").focus();
    });

    $("#id_barcode_copy").focusout(function (evt) {
        if ($("#id_barcode_copy").val().length === $("#id_barcode").val().length &&
            $('#id_barcode').val() != $("#id_barcode_copy").val()) {
            show_barcode_hide_placeholder();
        }
    });

    $("#id_barcode_copy").keyup(function (evt) {
        if ($("#id_barcode_copy").val().length === $("#id_barcode").val().length &&
            $("#id_barcode").val() === $("#id_barcode_copy").val()) {
            show_barcode_hide_placeholder();
            $("#id_barcode").parent().addClass('has-success');
            $("#id_barcode_copy").parent().addClass('has-success');
        } else if ($("#id_barcode_copy").val().length === $("#id_barcode").val().length) {
            show_barcode_hide_placeholder();
            $("#id_barcode").parent().removeClass('has-success');
            $("#id_barcode_copy").parent().removeClass('has-success');
            $("#id_barcode").parent().addClass('has-error');
            $("#id_barcode_copy").parent().addClass('has-error');
        } else {
            hide_barcode_show_placeholder();
        }
    });

    $("#id_barcode_copy").focusin(function (evt) {
        hide_barcode_show_placeholder();
    });
});

function change_barcode_entry_mode(barcode_entry_mode) {
    const id_form_instructions = document.getElementById('id_form_instructions');
    const barcode_manual_entry = document.getElementById('barcode_manual_entry');
    const barcode_scan_entry = document.getElementById('barcode_scan_entry');
    const barcode_scan_input_field = document.getElementById('id_scanned_barcode');
    const barcode_manual_entry_input_field = document.getElementById('id_barcode');
    const barcode_copy_manual_entry_input_field = document.getElementById('id_barcode_copy');
    const manual_entry_button = document.getElementById('manual_entry_button');
    const scanned_entry_button = document.getElementById('scanned_entry_button');
    const barcode_copy_manual_entry = document.getElementById('barcode_copy_manual_entry');

    if (barcode_entry_mode === 'manual') {
        id_form_instructions.innerText = 'Enter Barcode'
        barcode_scan_entry.setAttribute('hidden', 'true')
        barcode_manual_entry.removeAttribute('hidden');
        barcode_manual_entry_input_field.focus();
        barcode_manual_entry_input_field.setAttribute('required', 'true');
        barcode_copy_manual_entry_input_field.setAttribute('required', 'true');
        barcode_scan_input_field.removeAttribute('required');
        barcode_copy_manual_entry.removeAttribute('hidden');
        manual_entry_button.setAttribute('hidden', 'true')
        scanned_entry_button.removeAttribute('hidden');
        input_validation()
    }
    else if (barcode_entry_mode === 'scan') {
        id_form_instructions.innerText = 'Scan Barcode to proceed'
        barcode_manual_entry.setAttribute('hidden', 'true');
        barcode_copy_manual_entry.setAttribute('hidden', 'true');
        barcode_scan_entry.removeAttribute('hidden');
        barcode_scan_input_field.focus();
        barcode_scan_input_field.setAttribute('required', 'true');
        barcode_manual_entry_input_field.removeAttribute('required');
        barcode_copy_manual_entry_input_field.removeAttribute('required');
        scanned_entry_button.setAttribute('hidden', 'true');
        manual_entry_button.removeAttribute('hidden');
        barcode_scanner(barcode_scan_input_field);
    }

}