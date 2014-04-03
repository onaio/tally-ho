function loadTableData(url) {
    $(function(){
        $('#datalist').dataTable({
            "bPaginate": true,
            "iDisplayLength": 50,
            "bProcessing": true,
            "bServerSide": true,
            "sAjaxSource": Django.url(url),
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
