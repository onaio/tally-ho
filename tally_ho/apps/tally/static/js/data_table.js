function loadTableData(url) {
    var parsedUrl = url;

    try {
        parsedUrl = Django.url(url);
    } catch (DjangoJsError) {}

    $(function(){
        $('#datalist').dataTable({
            "bPaginate": true,
            "iDisplayLength": 50,
            "bProcessing": true,
            "bServerSide": true,
            "sAjaxSource": parsedUrl,
            "oLanguage": {
                "sLengthMenu": 'Display <select>'+
                    '<option value="10">10</option>'+
                    '<option value="25">25</option>'+
                    '<option value="50">50</option>'+
                    '<option value="100">100</option>'+
                    '<option value="500">500</option>'+
                    '</select> records'
            }
        });
    });
}
