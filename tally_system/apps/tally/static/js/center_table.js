$(function(){
    $('#centerlist').dataTable({
        "bPaginate": true,
        "iDisplayLength": 50,
        "bProcessing": true,
        "bServerSide": true,
        "sAjaxSource": Django.url('center-list-data')
    });
});
