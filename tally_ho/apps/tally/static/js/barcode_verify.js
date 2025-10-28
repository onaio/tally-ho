document.addEventListener("DOMContentLoaded", () => {
    const barcodeScanInputField = document.getElementById("id_scanned_barcode");
    const barcodeManualEntryInputField = document.getElementById("id_barcode");
    const barcodeCopyManualEntryInputField = document.getElementById("id_barcode_copy");
    // Set or remove required attributes based on form mode
    barcodeScanInputField.setAttribute("required", "true");
    barcodeManualEntryInputField.removeAttribute("required");
    barcodeCopyManualEntryInputField.removeAttribute("required");

    // Initialize auto-detection for manual typing in scan mode
    setup_scan_mode_typing_detection(barcodeScanInputField);
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

function show_error_msg(errorMessage) {    
    var form = document.getElementById("result_form");
    // Check if there's already an existing error div (from Django or previous JS call)
    var existingErrorDiv = form.querySelector(".text-danger");

    if(existingErrorDiv) {
        // Reuse existing div - only update if it doesn't already have our message
        // Check if the error message exists in any li element within the error div
        var existingErrorItems = existingErrorDiv.querySelectorAll("ul.errorlist li");
        var messageExists = Array.from(existingErrorItems).some(li => li.textContent === errorMessage);

        if(!messageExists) {
            // Clear any existing error lists before adding the new one
            var existingErrorLists = existingErrorDiv.querySelectorAll("ul.errorlist");
            existingErrorLists.forEach(list => list.remove());

            var errorList = document.createElement("ul");
            errorList.className = "errorlist nonfield";
            var errorItem = document.createElement("li");
            errorItem.textContent = errorMessage;
            errorList.appendChild(errorItem);
            existingErrorDiv.appendChild(errorList);
        }
        return;
    }

    // No existing error div found, create a new one
    var errorMsgDiv = document.createElement("div");
    errorMsgDiv.classList.add("text-danger");
    var errorList = document.createElement("ul");
    errorList.className ="errorlist nonfield";
    var errorItem = document.createElement("li"); 
    errorItem.textContent = errorMessage;
    errorList.appendChild(errorItem);
    errorMsgDiv.appendChild(errorList);
    form.insertBefore(errorMsgDiv, form.firstChild);
}

function hide_error_msg(errorMessage) {
    var form = document.getElementById("result_form");
    var errorDiv = form.querySelector(".text-danger");
    if (errorDiv && errorDiv.textContent.includes(errorMessage)) {
        errorDiv.remove();
    }
}

// Auto-detect manual typing vs barcode scanning
function setup_scan_mode_typing_detection(inputField) {
    let lastKeystrokeTime = 0;
    const TYPING_THRESHOLD_MS = 100; // If keystrokes are slower than 100ms apart, it's human typing
    let keystrokeCount = 0;
    const errorMessage = document.getElementById("error_msg_text").textContent;
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
            show_error_msg(errorMessage);

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
        hide_error_msg(errorMessage)
    });

    inputField.addEventListener("input", (event) => {
        if (event.target.value === "") {
            keystrokeCount = 0;
            lastKeystrokeTime = 0;
            hide_error_msg(errorMessage)
        }
    });
}