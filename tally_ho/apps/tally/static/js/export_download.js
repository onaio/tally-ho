$(document).ready(function () {
    $(".download-btn").on("click", function () {
        var $btn = $(this);
        var originalText = $btn.html();
        var url = $btn.data("url");

        $btn.html("Downloading...").prop("disabled", true);

        fetch(url)
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Server returned " + response.status);
                }
                var disposition = response.headers.get("Content-Disposition");
                var filename = "export.csv";
                if (disposition && disposition.indexOf("filename=") !== -1) {
                    filename = disposition.split("filename=")[1].replace(/"/g, "");
                }
                return response.blob().then(function (blob) {
                    return { blob: blob, filename: filename };
                });
            })
            .then(function (result) {
                var a = document.createElement("a");
                a.href = URL.createObjectURL(result.blob);
                a.download = result.filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                URL.revokeObjectURL(a.href);
                $btn.html(originalText).prop("disabled", false);
            })
            .catch(function () {
                $btn.html(originalText).prop("disabled", false);
                alert("Download failed. Please try again.");
            });
    });
});
