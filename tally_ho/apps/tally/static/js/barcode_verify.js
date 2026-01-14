document.addEventListener("DOMContentLoaded", () => {
    const barcodeScanInputField = document.getElementById("id_scanned_barcode");
    const barcodeManualEntryInputField = document.getElementById("id_barcode");
    const barcodeCopyManualEntryInputField = document.getElementById("id_barcode_copy");
    const submitButton = document.getElementById("barcode_submit_btn");

    // Set or remove required attributes based on form mode
    barcodeScanInputField.setAttribute("required", "true");
    barcodeManualEntryInputField.removeAttribute("required");
    barcodeCopyManualEntryInputField.removeAttribute("required");

    // Initialize submit button state check
    check_submit_button_state();

    // Add input event listeners to check barcode length
    barcodeScanInputField.addEventListener("input", check_submit_button_state);
    barcodeManualEntryInputField.addEventListener("input", check_submit_button_state);
    barcodeCopyManualEntryInputField.addEventListener("input", check_submit_button_state);

    // Initialize auto-detection for manual typing in scan mode
    setup_scan_mode_typing_detection(barcodeScanInputField);
});

// Check submit button state based on barcode length
function check_submit_button_state() {
    const barcodeScanInputField = document.getElementById("id_scanned_barcode");
    const barcodeManualEntryInputField = document.getElementById("id_barcode");
    const barcodeCopyManualEntryInputField = document.getElementById("id_barcode_copy");
    const submitButton = document.getElementById("barcode_submit_btn");
    const barcodeScanEntry = document.getElementById("barcode_scan_entry");
    const barcodeManualEntry = document.getElementById("barcode_manual_entry");
    const validBarcodeLength = 11; 
    if (!submitButton) return;

    // Check which mode we're in and validate accordingly
    if (barcodeScanEntry && !barcodeScanEntry.hidden) {
        // Scan mode: check if scanned barcode is at least 11 characters
        const barcodeLength = barcodeScanInputField.value.length;
        submitButton.disabled = barcodeLength < validBarcodeLength;
    } else if (barcodeManualEntry && !barcodeManualEntry.hidden) {
        // Manual entry mode: check if both barcode fields are at least 11 characters
        const barcodeLength = barcodeManualEntryInputField.value.length;
        const barcodeCopyLength = barcodeCopyManualEntryInputField.value.length;
        submitButton.disabled = barcodeLength < validBarcodeLength || barcodeCopyLength < validBarcodeLength;
    }
}

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
        check_submit_button_state();
        hide_error_msg();
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
        check_submit_button_state();
    }
}

function show_error_msg() {
    jQuery("#manual_entry_error_msg").show();
}

function hide_error_msg() {
    jQuery("#manual_entry_error_msg").hide();
}

// Auto-detect manual typing vs barcode scanning
function setup_scan_mode_typing_detection(inputField) {
    let lastKeystrokeTime = 0;
    const TYPING_THRESHOLD_MS = 100; // If keystrokes are slower than 100ms apart, it's human typing
    let keystrokeCount = 0;

    inputField.addEventListener("keydown", () => {
        const currentTime = Date.now();
        const timeSinceLastKeystroke = currentTime - lastKeystrokeTime;

        keystrokeCount++;

        // If this is the second keystroke and it's slower than threshold, switch to manual mode
        // We check on the second keystroke to avoid switching on the first character
        if (keystrokeCount >= 2 && timeSinceLastKeystroke > TYPING_THRESHOLD_MS) {
            // Clear the scan field
            inputField.value = "";

            // show error message
            show_error_msg();

            // Reset detection for next time
            keystrokeCount = 0;
            lastKeystrokeTime = 0;
            return;
        }

        lastKeystrokeTime = currentTime;
    });

    // Reset detection when field is cleared or loses focus
    inputField.addEventListener("blur", () => {
        keystrokeCount = 0;
        lastKeystrokeTime = 0;
    });

    inputField.addEventListener("input", (event) => {
        if (event.target.value === "") {
            keystrokeCount = 0;
            lastKeystrokeTime = 0;
            hide_error_msg();
        }
    });
}