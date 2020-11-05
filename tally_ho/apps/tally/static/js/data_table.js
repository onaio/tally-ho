$(document).ready(function () {
  $('.datatable').DataTable({
    language: dt_language, // global variable defined in html
    order: [[0, 'desc']],
    lengthMenu: [
      [10, 25, 50, 100, 500],
      [10, 25, 50, 100, 500],
    ],
    columnDefs: [
      {
        orderable: true,
        searchable: true,
        className: 'center',
        targets: [0, 1],
      },
    ],
    searching: true,
    processing: true,
    serverSide: true,
    stateSave: true,
    ajax: LIST_JSON_URL,
    dom: 'Bfrtip',
    buttons: [
      {
        extend: 'csv',
        filename: exportFileName,
      },
    ],
    select: 'multi',
  });
});
