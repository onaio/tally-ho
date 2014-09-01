$(function(){
    $('#formauditpendinglist').dataTable({
        "bPaginate": true,
        "iDisplayLength": 50,
        "bProcessing": true,
        "bServerSide": true,
        "sAjaxSource": Django.url('form-audit-data')
    });
});
