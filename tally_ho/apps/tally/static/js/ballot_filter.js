$(document).ready(function() {
    // Handle the show inactive ballots checkbox
    $('#show-inactive-ballots').on('change', function() {
        var isChecked = $(this).is(':checked');
        var url = new URL(window.location.href);

        if (isChecked) {
            url.searchParams.set('show_inactive', 'true');
        } else {
            url.searchParams.delete('show_inactive');
        }

        // Reload the page with the updated URL
        window.location.href = url.toString();
    });
});
