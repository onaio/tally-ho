function set_as_printed() {
    if ($("#printed-url").length > 0) {
        $.ajax({
            url: $("#printed-url").attr("data-url"),
            timeout: 10000,
            success(data) {}
        });
    }
}


function print_cover() {
    window.print();
    set_as_printed();
    document.getElementById("submit_cover_form").setAttribute("style", "display: inline");
}
