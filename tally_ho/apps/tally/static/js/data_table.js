$(document).ready(function () {
  pdfMake.fonts = {
    Arial: {
        normal: arialNormal,
        bold: arialBold,
        italics: arialItalics,
        bolditalics: arialBItalics
    }
};

  const exportFiltersApplied = ({
    stations,
    centers,
    races,
  }) => {
    let filters = ``;
    let count = 0;

    if (!races.includes('Select')) {
      filters += `Races: ${races}\n`
      count++
    }

    if (!centers.includes('Select')) {
      filters += `Centers: ${centers}\n`
      count++
    }

    if (!stations.includes('Select')) {
      filters += `Stations: ${stations}\n`
      count++
    }
    
    return { filters, count }
}

  const exportPdfHtml5 = doc => {
    const logo = 'data:image/png;base64,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'
    const numRecordsToExport = parseInt($('input#export-number').val());
    let pdfHeaders = [
      {
          image: logo,
          width: 90,
          height: 24,
      },
      {
          alignment: 'center',
          italics: true,
          text: `Top ${numRecordsToExport} Leading Candidate Results Report`,
          fontSize: 18,
          margin: [10,0],
      },
    ];

    const filtersIncluded = exportFiltersApplied({
      stations: $("button[data-id='filter-in-stations']").attr('title'),
      centers: $("button[data-id='filter-in-centers']").attr('title'),
      races: $("button[data-id='filter-in-race-types']").attr('title'),
      ballot_status: $("button[data-id='ballot-status']").attr('title'),
      station_status: $("button[data-id='station-status']").attr('title'),
      candidate_status: $("button[data-id='candidate-status']").attr('title'),
      percentage_processed: $("input[data-id='percentage-processed']").attr('title'),
    });
    const filtersExcluded = exportFiltersApplied({
      stations: $("button[data-id='stations']").attr('title'),
      centers: $("button[data-id='centers']").attr('title'),
      races: $("button[data-id='filter-out-race-types']").attr('title'),
    });
    let filters = []
    const searchVal = $("input[type='search']").val()
    if (filtersIncluded.count > 0) {
      let text = `Filters Included: \n\n${filtersIncluded.filters}`;
      if (searchVal !== '') {
        text = text + `Search: ${searchVal}`
      }
      filters = [
        ...filters,
        {
          style: 'subheader',
          alignment: 'left',
          text: text,
        }
      ];
    }

    if (filtersExcluded.count > 0) {
      let text = `Filters Excluded: \n\n${filtersExcluded.filters}`;
      if (searchVal !== '') {
        text = text + `Search: ${searchVal}`
      }
      filters = [
        ...filters,
        {
          style: 'subheader',
          alignment: 'left',
          text: text,
        }];
    }
    //Remove the title created by datatTables
    doc?.content?.splice(0,2);
    const totalRecords = doc?.content[0]?.table?.body?.length - 1
    const numRecordsToSplice = totalRecords - numRecordsToExport;
    if (numRecordsToSplice) {
      const spliceStartIndex = totalRecords - numRecordsToSplice;
      doc?.content[0]?.table?.body?.splice(spliceStartIndex, numRecordsToSplice)
    }
    //Create a date string that we use in the footer. Format is dd-mm-yyyy
    const now = new Date();
    const jsDate = now.getDate()+'-'+(now.getMonth()+1)+'-'+now.getFullYear();
    doc.pageMargins = [20,60,20,30];
    // Set the font size fot the entire document
    doc.defaultStyle.fontSize = 7;
    doc.defaultStyle.font = 'Arial';
    // Set the fontsize for the table header
    doc.styles.tableHeader.fontSize = 7;
    // Right side: A document title
    doc['header']=(function() {
        return {
            alignment: 'justify',
            columns: pdfHeaders,
            margin: 20
        }
    });
    // Create a footer object with 2 columns
    // Left side: report creation date
    // Right side: current page and total pages
    doc['footer']=(function(page, pages) {
        return {
            columns: [
                {
                    alignment: 'left',
                    text: ['Created on: ', { text: jsDate.toString() }]
                },
                {
                    alignment: 'right',
                    text: ['page ', { text: page.toString() },	' of ',	{ text: pages.toString() }]
                }
            ],
            margin: 20
        }
    });
    // Change dataTable layout (Table styling)
    // To use predefined layouts uncomment the line below and comment the custom lines below
    // doc.content[0].layout = 'lightHorizontalLines'; // noBorders , headerLineOnly
    const objLayout = {};
    objLayout['hLineWidth'] = function(i) { return .5; };
    objLayout['vLineWidth'] = function(i) { return .5; };
    objLayout['hLineColor'] = function(i) { return '#aaa'; };
    objLayout['vLineColor'] = function(i) { return '#aaa'; };
    objLayout['paddingLeft'] = function(i) { return 4; };
    objLayout['paddingRight'] = function(i) { return 4; };
    doc.content[0].layout = objLayout;
    doc['content'] = [
      {
        columns: filters,
        margin: [0, 15]
      },
      ...doc?.content,
    ]
    };
  const resetFilters = (attributesList) => {
    for (let i = 0; i < attributesList.length; i++) {
        $(attributesList[i]).val(null);
        $(attributesList[i]).change();
    }
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
          for (let i = 0; i < d.columns.length - 1; i++) {
            d[`columns[${i}][data]`] = d.columns[i].data
            d[`columns[${i}][name]`] = d.columns[i].name
            d[`columns[${i}][searchable]`] = d.columns[i].searchable
            d[`columns[${i}][search][value]`] = d.columns[i].search.value
            d[`columns[${i}][search][regex]`] = d.columns[i].search.regex
            d[`columns[${i}][data]`] = d.columns[i].data
          }
          d['order[0][column]'] = d.columns[d.order[0].column].data;
          d['order[0][dir]'] = d.order[0].dir;
          d['search[value]'] = d.search.value;
          d['search[regex]'] = d.search.regex;
          d['columns'] = d.columns;
          d['order'] = d.order;
          d['draw'] = d.draw;
          d['start'] = d.start;
          d['length'] = d.length;
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
      responsive: true,
    });
    return table;
  }

  // Initialize table
  const table = createTable();


  $('#in-report').on('click', '#reset-filters-in-report', function () {
    const attributesList = ['select#election-level-names', 'select#sub-race-names', 'select#filter-in-centers', 'select#filter-in-stations', 'select#ballot-status', 'select#station-status', 'select#candidate-status', 'input#percentage-processed'];
    resetFilters(attributesList);
    table.settings()[0].ajax.data = function(d) {
      d.data = JSON.stringify([]);
    };
    table.ajax.reload();
  });


  $('#in-report').on('click', '#filter-in-report', function () {
    let data = [];
    let selectOneIds = $('select#filter-in-centers').val();
    let selectTwoIds = $('select#filter-in-stations').val();
    let exportNumber = $('input#export-number').val();
    let electionLevelNames = $('select#election-level-names').val();
    let subRaceTypeNames = $('select#sub-race-names').val();
    let ballotStatus = $('select#ballot-status').val();
    let stationStatus = $('select#station-status').val();
    let candidateStatus = $('select#candidate-status').val();
    let percentageProcessed = $('input#percentage-processed').val();

    if (selectOneIds || selectTwoIds) {
      const items = {
        select_1_ids: selectOneIds !== null ? selectOneIds : [],
        select_2_ids: selectTwoIds !== null ? selectTwoIds : [],
        export_number: exportNumber !== null ? exportNumber : [],
        election_level_names: electionLevelNames !== null ? electionLevelNames : [],
        sub_race_type_names: subRaceTypeNames !== null ? subRaceTypeNames : [],
        ballot_status: ballotStatus !== null ? ballotStatus : [],
        station_status: stationStatus !== null ? stationStatus : [],
        candidate_status: candidateStatus !== null ? candidateStatus : [],
        percentage_processed: percentageProcessed !== null ? percentageProcessed : [],
        filter_in: "True"
      };

      data = items;
    }

    data = data.length
      ? data.filter((item) =>
          Object.values(item).every((value) => typeof value !== 'undefined')
        )
      : data;

    table.settings()[0].ajax.data = function(d) {
      d.data = JSON.stringify(data);
    };

    table.ajax.reload();
  });

  $('#in-report').on('click', '#inc-ppt-export-report', function () {
    $("#inc-ppt-export-report").html("Exporting...");
    $("#inc-ppt-export-report").prop("disabled", true);

    let data = [];
    let selectOneIds = $('select#filter-in-centers').val();
    let selectTwoIds = $('select#filter-in-stations').val();
    let electionLevelNames = $('select#election-level-names').val();
    let subRaceTypeNames = $('select#sub-race-names').val();
    let exportNumber = $('input#export-number').val();
    let ballotStatus = $('select#ballot-status').val();
    let stationStatus = $('select#station-status').val();
    let candidateStatus = $('select#candidate-status').val();
    let percentageProcessed = $('input#percentage-processed').val();

    const downloadFile = (blob, fileName) => {
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = fileName;
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(link.href), 7000);
    };


    const items = {
      select_1_ids: selectOneIds !== null ? selectOneIds : [],
      select_2_ids: selectTwoIds !== null ? selectTwoIds : [],
      election_level_names: electionLevelNames !== null ? electionLevelNames : [],
      sub_race_type_names: subRaceTypeNames !== null ? subRaceTypeNames : [],
      export_number: exportNumber !== null ? exportNumber : [],
      ballot_status: ballotStatus !== null ? ballotStatus : [],
      station_status: stationStatus !== null ? stationStatus : [],
      candidate_status: candidateStatus !== null ? candidateStatus : [],
      percentage_processed: percentageProcessed !== null ? percentageProcessed : [],
      tally_id: tallyId,
      exportType: "PPT",
      filter_in: "True",
    };
    data = items;


    data = data.length
      ? data.filter((item) =>
          Object.values(item).every((value) => typeof value !== 'undefined')
        )
      : data;

     $.ajax({
        url: getExportUrl,
        data: { data: JSON.stringify(data) },
        traditional: true,
        type: 'GET',
        xhrFields: {
          responseType: 'blob'
        },
        success: (data) => {
          if (data?.size === undefined) {
            alert('No Data')
          } else {
            downloadFile(data, 'election_results.pptx');
          }
          $("#inc-ppt-export-report").html("PowerPoint Export");
          $("#inc-ppt-export-report").prop("disabled", false);
        },
        error: function(xhr, status, error) {
          console.log('Error:', error);
          $("#inc-ppt-export-report").html("PowerPoint Export");
          $("#inc-ppt-export-report").prop("disabled", false);
        }
    });
  });
});
