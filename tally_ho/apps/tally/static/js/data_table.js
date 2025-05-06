$(document).ready(function () {
  pdfMake.fonts = {
    Arial: {
      normal: arialNormal,
      bold: arialBold,
      italics: arialItalics,
      bolditalics: arialBItalics,
    },
  };

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

  const buildTablePayload = (d, customPayloadObj=undefined) => {
    let payload = d;
    if (customPayloadObj) {
      payload = {
        ...payload,
        ...customPayloadObj,
      }
    }
    for (let i = 0; i < payload.columns.length - 1; i++) {
      payload[`columns[${i}][data]`] = payload.columns[i].data
      payload[`columns[${i}][name]`] = payload.columns[i].name
      payload[`columns[${i}][searchable]`] = payload.columns[i].searchable
      payload[`columns[${i}][search][value]`] = payload.columns[i].search.value
      payload[`columns[${i}][search][regex]`] = payload.columns[i].search.regex
      payload[`columns[${i}][data]`] = payload.columns[i].data
    }
    payload['order[0][column]'] = payload.columns[payload.order[0].column].data;
    payload['order[0][dir]'] = payload.order[0].dir;
    payload['search[value]'] = payload.search.value;
    payload['search[regex]'] = payload.search.regex;
    payload['columns'] = payload.columns;
    payload['order'] = payload.order;
    payload['draw'] = payload.draw;
    payload['start'] = payload.start;
    payload['length'] = payload.length;

    return payload
  }

  const createTable = () => {
    const table = $('.datatable').DataTable({
      language: dt_language, // global variable defined in html
      order: [[0, "desc"]],
      lengthMenu: [
        [10, 25, 50, 100, 500, -1],
        [10, 25, 50, 100, 500, 'Show all'],
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
      serverMethod: "post",
      ajax: {
        url: LIST_JSON_URL,
        type: 'POST',
        data: (d) => {
          return buildTablePayload(d);
        },
        traditional: true,
        dataType: 'json',
      },
      dom:
        "<'row'<'col-sm-2'B><'col-sm-6'l><'col-sm-4'f>>" +
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
        // Commented out since it's being replaced by PPT export
        // Will need to be made generic incase it's need in future
        // {
        //   text: 'PDF',
        //   extend: 'pdfHtml5',
        //   filename: 'form_results_export',
        //   orientation: 'landscape', //portrait
        //   pageSize: 'A4', //A3 , A5 , A6 , legal , letter
        //   exportOptions: {
        //       columns: ':visible :not(.hide-from-export)',
        //       modifier: {
        //         selected: null,
        //       }
        //   },
        //   customize: (doc) => {
        //     exportPdfHtml5(doc);
        //   },
        //       },
      ],
      responsive: enableResponsive,
      scrollX: enableScrollX,
    });
    return table;
  }

  // Initialize table
  const table = createTable();

  $('#report').on('click', '#filter-report', () => {
    let data = [];
    let selectOneIds = $('select#centers').val();
    let selectTwoIds = $('select#stations').val();

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

    table.settings()[0].ajax.data = (d) => {
      return buildTablePayload(d, { data: JSON.stringify(data) });
    };

    table.ajax.reload();
  });

});
