let barcodeNumber = "";

const barcode_scanner = (barcodeInputField) => {
    let typingTimeout;

    if (barcodeInputField) {
        barcodeInputField.addEventListener("keypress", function (e) {
            // Reset the timeout on each keypress
            clearTimeout(typingTimeout);

            if (e.key === "Enter") {
                barcodeInputField.value = barcodeNumber;
                barcodeInputField.readOnly = true;
                barcodeNumber = ""; // Reset after a full scan is detected
            } else if (!isNaN(e.key)) {
                barcodeNumber += e.key; // Append numeric input
            }

            // Set a timeout to reset if no key is pressed in 200ms (example debounce time)
            typingTimeout = setTimeout(() => {
                barcodeNumber = "";
            }, 200);
        });
    }
};

document.addEventListener("DOMContentLoaded", () => {
    const barcodeScanInputField = document.getElementById("id_scanned_barcode");
    const barcodeManualEntryInputField = document.getElementById("id_barcode");
    const barcodeCopyManualEntryInputField = document.getElementById("id_barcode_copy");

    barcodeNumber = "";
    barcode_scanner(barcodeScanInputField);

    // Set or remove required attributes based on form mode
    barcodeScanInputField.setAttribute("required", "true");
    barcodeManualEntryInputField.removeAttribute("required");
    barcodeCopyManualEntryInputField.removeAttribute("required");
});

// Utility functions for showing and hiding placeholders
function show_barcode_hide_placeholder() {
    $("#barcode_placeholder").hide();
    $("#id_barcode").show();
}

function hide_barcode_show_placeholder() {
    $("#barcode_placeholder").show();
    $("#id_barcode").hide();
}

// Enhanced input validation
function input_validation() {
    $("#id_barcode").on("focusout", () => {
        if ($("#id_barcode").val() && $("#id_barcode_copy").val() !== $("#id_barcode").val()) {
            hide_barcode_show_placeholder();
        }
    });

    $("#id_barcode_copy").on("focusout keyup", () => {
        if ($("#id_barcode_copy").val().length === $("#id_barcode").val().length &&
            $("#id_barcode").val() === $("#id_barcode_copy").val()) {
            show_barcode_hide_placeholder();
            $("#id_barcode, #id_barcode_copy").parent().addClass("has-success");
        } else if ($("#id_barcode_copy").val().length === $("#id_barcode").val().length) {
            show_barcode_hide_placeholder();
            $("#id_barcode, #id_barcode_copy").parent().removeClass("has-success").addClass("has-error");
        } else {
            hide_barcode_show_placeholder();
        }
    });
}

// Toggle between barcode entry modes
function change_barcode_entry_mode(barcodeEntryMode) {
    const idFormInstructions = document.getElementById("id_form_instructions");
    const barcodeManualEntry = document.getElementById("barcode_manual_entry");
    const barcodeScanEntry = document.getElementById("barcode_scan_entry");
    const barcodeScanInputField = document.getElementById("id_scanned_barcode");
    const barcodeManualEntryInputField = document.getElementById("id_barcode");
    const barcodeCopyManualEntryInputField = document.getElementById("id_barcode_copy");
    const manualEntryButton = document.getElementById("manual_entry_button");
    const scannedEntryButton = document.getElementById("scanned_entry_button");
    const barcodeCopyManualEntry = document.getElementById("barcode_copy_manual_entry");

    if (barcodeEntryMode === "manual") {
        idFormInstructions.innerText = "Enter Barcode";
        barcodeScanEntry.hidden = true;
        barcodeManualEntry.hidden = false;
        barcodeManualEntryInputField.required = true;
        barcodeCopyManualEntryInputField.required = true;
        barcodeScanInputField.removeAttribute("required");
        barcodeCopyManualEntry.hidden = false;
        manualEntryButton.hidden = true;
        scannedEntryButton.hidden = false;
        input_validation();
    } else if (barcodeEntryMode === "scan") {
        idFormInstructions.innerText = "Scan Barcode to proceed";
        barcodeManualEntry.hidden = true;
        barcodeCopyManualEntry.hidden = true;
        barcodeScanEntry.hidden = false;
        barcodeScanInputField.focus();
        barcodeScanInputField.required = true;
        barcodeManualEntryInputField.removeAttribute("required");
        barcodeCopyManualEntryInputField.removeAttribute("required");
        manualEntryButton.hidden = false;
        scannedEntryButton.hidden = true;
        barcode_scanner(barcodeScanInputField);
    }
}
