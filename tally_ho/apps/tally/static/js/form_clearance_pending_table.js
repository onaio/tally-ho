$(function(){
    $('#formclearancependinglist').dataTable({
        "bPaginate": true,
        "iDisplayLength": 50,
        "bProcessing": true,
        "bServerSide": true,
        "sAjaxSource": Django.url('form-clearance-pending-data')
    });
});
