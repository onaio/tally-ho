$(document).ready(function (dt_language, serverSide, LIST_JSON_URL, exportFileName) {

  $(".datatable").dataTable({
    language: dt_language, // global variable defined in html
    order: [[0, "desc"]],
    lengthMenu: [
      [10, 25, 50, 100, 500],
      [10, 25, 50, 100, 500],
    ],
    columnDefs: [
      {
        orderable: true,
        searchable: true,
        className: "center",
        targets: [0, 1],
      },
    ],
    searching: true,
    processing: true,
    serverSide: serverSide,
    stateSave: true,
    ajax: LIST_JSON_URL,
    dom:
      "<'row'<'col-sm-1'B><'col-sm-6'l><'col-sm-5'f>>" +
      "<'row'<'col-sm-12'tr>>" +
      "<'row'<'col-sm-5'i><'col-sm-7'p>>",
    buttons: [
      {
        extend: "csv",
        filename: exportFileName,
        exportOptions: {
          columns: ":visible :not(.actions)",
        },
      },
    ],
    select: {
      style: "multi",
    },
    responsive: true,
  });
});
