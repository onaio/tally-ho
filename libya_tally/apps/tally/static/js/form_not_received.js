$(function(){
    $('#formlist').dataTable({
        "bPaginate": true,
        "iDisplayLength": 50,
        "bProcessing": true,
        "bServerSide": true,
        "sAjaxSource": Django.url('form-not-received-data')
    });
});
