$(document).ready(function () {
    // TODO - WET CODE ALERT!!!!!
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
  $('#regions').change(function () {
    const region_names = $('#regions').val();

    if (region_names) {
      $.ajax({
        url: getSubAndConstituenciesUrl,
        data: {
          data: JSON.stringify({
            region_names: region_names,
            tally_id: tallyId,
          }),
        },
        traditional: true,
        dataType: 'json',
        success: (data) => {
          const { constituency_names, sub_constituencies_code } = data;
          $('#constituencies').selectpicker('val', constituency_names);
          $('#sub_constituencies').selectpicker('val', sub_constituencies_code);
        },
      });
    } else {
       $('#constituencies').selectpicker('deselectAll');
       $('#sub_constituencies').selectpicker('deselectAll');
       $('#constituencies').selectpicker('refresh');
          $('#sub_constituencies').selectpicker('refresh');
    }
  });
    $('#report').on('click', '#filter-report', function () {
    const table = $('.datatable').DataTable();

    table.destroy();
    let filters = {};
    let regions = $('select#regions').val();
    let constituencies = $('select#constituencies').val();
    let sub_constituencies = $('select#sub_constituencies').val();

    filters.region_names = regions ? regions: undefined
    filters.constituencies = constituencies ? constituencies: undefined
    filters.sub_constituencies = sub_constituencies ? sub_constituencies: undefined

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
        data: { data: JSON.stringify(filters) },
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
          action: exportAction,
          exportOptions: {
            columns: ':visible :not(.actions)',
          },
        },
      ],
      responsive: true,
    });
  });

});
