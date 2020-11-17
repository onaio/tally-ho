$(document).ready(function () {
  const exportAction = function (e, dt, button, config) {
    const self = this;
    const oldStart = dt.settings()[0]._iDisplayStart;
    dt.one('preXhr', function (e, s, data) {
        // Just this once, load all data from the server...
        data.start = 0;
        data.length = -1;;
        dt.one('preDraw', function (e, settings) {
            if (button[0].className.indexOf('buttons-csv') >= 0) {
                $.fn.dataTable.ext.buttons.csvHtml5.available(dt, config) ?
                    $.fn.dataTable.ext.buttons.csvHtml5.action.call(self, e, dt, button, config) :
                    $.fn.dataTable.ext.buttons.csvFlash.action.call(self, e, dt, button, config);
            }
            dt.one('preXhr', function (e, s, data) {
                // DataTables thinks the first item displayed is index 0, but we're not drawing that.
                // Set the property to what it was before exporting.
                settings._iDisplayStart = oldStart;
                data.start = oldStart;
            });
            // Reload the grid with the original page. Otherwise, API functions like table.cell(this) don't work properly.
            setTimeout(dt.ajax.reload, 0);
            // Prevent rendering of the full data to the DOM
            return false;
        });
    });
    // Requery the server with the new one-time export settings
    dt.ajax.reload();
  };
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
        action: exportAction,
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
    let selectOneIds = $('select#select-1').val()
    let selectTwoIds = $('select#select-2').val()

    if (selectOneIds || selectTwoIds) {
      const items = {
        select_1_ids: selectOneIds !== null ? selectOneIds : [],
        select_2_ids: selectTwoIds !== null ? selectTwoIds : [],
      };

      data = items;
    } else {
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
    }

    data = data.length
      ? data.filter((item) =>
          Object.values(item).every((value) => typeof value !== 'undefined')
        )
      : data;

    $('.datatable').dataTable({
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
