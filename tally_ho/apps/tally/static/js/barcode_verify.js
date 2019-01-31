function barcodes_match(empty_message, length_message, mismatch_message) {
    var barcode = document.getElementById('id_barcode');
    var barcode_copy = document.getElementById('id_barcode_copy');
    const barcode_manual_entry = () => document.getElementById('barcode_manual_entry');
    if (barcode_manual_entry() != null){
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
    }else{
        return;
    }

    return false;
}

var barcode_number = '';

const barcode_scanner = (barcode_input_field) => {
    if (barcode_input_field()) {
        barcode_input_field().addEventListener('keydown', function (e) {
            e.preventDefault();
            const textInput = e.key
            if (textInput.length === 1 || (e.keyCode === 13)) {
                if (e.code == 'KeyA') {
                    barcode_number = barcode_number + textInput;
                }
                if (barcode_number && (e.keyCode === 13)) {
                    barcode_input_field().value = barcode_number;
                    barcode_input_field().readOnly = true;
                }
            }

        });
    }
}

document.onreadystatechange = function () {
    if (document.readyState == "complete") {
        const barcode_scan_input_field = () => document.getElementById('id_scanned_barcode');
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
        if ($("#id_barcode_copy").val().length == $("#id_barcode").val().length &&
            $('#id_barcode').val() != $("#id_barcode_copy").val()) {
            show_barcode_hide_placeholder();
        }
    });

    $("#id_barcode_copy").keyup(function (evt) {
        if ($("#id_barcode_copy").val().length == $("#id_barcode").val().length &&
            $("#id_barcode").val() == $("#id_barcode_copy").val()) {
            show_barcode_hide_placeholder();
            $("#id_barcode").parent().addClass('has-success');
            $("#id_barcode_copy").parent().addClass('has-success');
        } else if ($("#id_barcode_copy").val().length == $("#id_barcode").val().length) {
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

function add_element(elementTag, elementId, html) {
    const table = document.getElementById("formtablebody");
    const newElement = document.createElement(elementTag);
    newElement.setAttribute('id', elementId)
    newElement.innerHTML = html;
    table.insertBefore(newElement, table.firstChild);
}


function change_barcode_entry_mode(barcode_entry_mode) {
    const result_form = document.getElementById('result_form');
    const id_form_instructions = document.getElementById('id_form_instructions');
    const barcode_manual_entry = document.getElementById('barcode_manual_entry');
    const barcode_scanned_entry = document.getElementById('barcode_scanned_entry');
    const barcode_scan_input_field = () => document.getElementById('id_scanned_barcode');
    const barcode_manual_input_field = () => document.getElementById('id_barcode');
    const manual_entry_button = () => document.getElementById('manual_entry_button');
    const scanned_entry_button = () => document.getElementById('scanned_entry_button');
    const barcode_copy_manual_entry = document.getElementById('barcode_copy_manual_entry');
    const table = document.getElementById("formtablebody");
    const barcode_errors_section = () => document.getElementById('barcode_errors');

    if (barcode_entry_mode == 'manual') {
        table.removeChild(barcode_scanned_entry)
        barcode_input_html = '<td><label>Barcode</label></td>' +
            '<td><input type="number" name="barcode" oncopy="return false;" ondrag="return false;" ondrop="return false;" onpaste="return false;" autocomplete="off" class="form-control" autofocus="on" required="" id="id_barcode">' +
            '<input type="password" class="form-control" value="XXXXXXXX" name="barcode_placeholder" id="barcode_placeholder" style="display:none;"></td>'
        barcode_copy_input_html = '<td><label>Barcode Copy</label></td>' +
            '<td><input type="number" name="barcode_copy" oncopy="return false;" ondrag="return false;" ondrop="return false;" onpaste="return false;" autocomplete="off" class="form-control" required="" id="id_barcode_copy"></td>'
        id_form_instructions.innerText = 'Enter Barcode'
        add_element('tr', 'barcode_copy_manual_entry', barcode_copy_input_html)
        add_element('tr', 'barcode_manual_entry', barcode_input_html)
        barcode_manual_input_field().focus();
        manual_entry_button().setAttribute('hidden', 'true')
        scanned_entry_button().removeAttribute('hidden');
        input_validation()
    }
    else if (barcode_entry_mode == 'scan') {
        table.removeChild(barcode_manual_entry)
        table.removeChild(barcode_copy_manual_entry)
        barcode_scan_input_html = '<td><label>Barcode</label></td>' +
                                  '<input type="text" name="barcode" autocomplete="off" class="form-control" id="id_scanned_barcode" autofocus>'
        id_form_instructions.innerText = 'Scan Barcode to proceed'
        add_element('tr', 'barcode_scanned_entry', barcode_scan_input_html)
        barcode_scan_input_field().value = ''
        barcode_scan_input_field().readOnly = false
        barcode_number = ''
        scanned_entry_button().setAttribute('hidden', 'true')
        manual_entry_button().removeAttribute('hidden');
        barcode_scan_input_field().focus();
        barcode_scanner(barcode_scan_input_field)
    }

    if (barcode_errors_section() != null) {
        result_form.removeChild(barcode_errors_section())
    }
}