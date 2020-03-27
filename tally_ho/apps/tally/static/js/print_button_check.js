function print_cover() {
    window.print();
    set_as_printed();
    document.getElementById("submit_cover_form").setAttribute("style", "display: inline");
}


function set_as_printed() {
    if ($("#printed-url").length > 0) {
        console.log($("#printed-url").attr("data-url"));

        $.ajax({
            url: $("#printed-url").attr("data-url"),
            timeout: 10000,
            success: function (data) {}
        });
    }
}
