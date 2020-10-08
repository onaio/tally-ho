$(document).ready(function () {
  $('.datatable').dataTable({
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
    serverSide,
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
          columns: ':visible :not(.hide-from-export)',
        },
      },
    ],
    select: {
      style: "multi",
    },
    responsive: true,
  });

  $('#report').on('click', '#filter-report', function () {
    const table = $('.datatable').DataTable();

    table.destroy();
    let data = [];
    $('tbody tr').each(function (i, row) {
      const selectOneElement = $(row).find('select#select-1');
      const selectTwoElement = $(row).find('select#select-2');

      const items = {
        select_1_ids:
          selectOneElement.val() !== null ? selectOneElement.val() : [],
        select_2_ids:
          selectTwoElement.val() !== null ? selectTwoElement.val() : [],
        region_id: selectOneElement.attr('data-id'),
      };
      data.push(items);
    });
    data = data.length
      ? data.filter((item) =>
          Object.values(item).every((value) => typeof value !== 'undefined')
        )
      : data;

    $('#report').dataTable({
      language: dt_language,
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
      ajax: {
        url: LIST_JSON_URL,
        type: 'POST',
        data: { data: JSON.stringify(data) },
        traditional: true,
        dataType: 'json',
      },
      dom:
        "<'row'<'col-sm-1'B><'col-sm-6'l><'col-sm-5'f>>" +
        "<'row'<'col-sm-12'tr>>" +
        "<'row'<'col-sm-5'i><'col-sm-7'p>>",
      buttons: [
        {
          extend: 'csv',
          filename: exportFileName,
          exportOptions: {
            columns: ':visible :not(.actions)',
          },
        },
      ],
      responsive: true,
    });
  });
});
