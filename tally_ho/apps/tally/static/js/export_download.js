$(document).ready(function () {
    $(".download-btn").on("click", function () {
        var $btn = $(this);
        var originalText = $btn.text();
        $btn.text("Downloading...").prop("disabled", true);

        var iframe = document.createElement("iframe");
        iframe.style.display = "none";
        iframe.src = $btn.data("url");
        document.body.appendChild(iframe);

        // Restore button after response headers arrive
        // With streaming, this happens quickly
        var timeout = setTimeout(function () {
            $btn.text(originalText).prop("disabled", false);
            if (iframe.parentNode) {
                document.body.removeChild(iframe);
            }
        }, 10000);

        iframe.onerror = function () {
            clearTimeout(timeout);
            $btn.text(originalText).prop("disabled", false);
            if (iframe.parentNode) {
                document.body.removeChild(iframe);
            }
            alert("Download failed. Please try again.");
        };
    });
});
