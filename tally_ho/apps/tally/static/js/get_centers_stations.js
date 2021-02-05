$(document).ready(function () {
  $('#centers').change(function () {
    const center_ids = $('.selectpicker').val();

    if (center_ids) {
      $.ajax({
        url: getCentersStationsUrl,
        data: {
          data: JSON.stringify({
            center_ids: center_ids,
            tally_id: tallyId,
          }),
        },
        traditional: true,
        dataType: 'json',
        success: (data) => {
          const { station_ids } = data;
          $('.center-stations').selectpicker('val', station_ids);
        },
      });
    } else {
      $('.center-stations').selectpicker('deselectAll');
      $('.center-stations').selectpicker('refresh');
    }
  });
});
