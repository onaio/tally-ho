var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();

function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i]);
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

if (typeof csrftoken === "undefined") csrftoken = getCookie("csrftoken");

var currentStep = 0;
var totalSteps = 7;

for (var i = 1; i <= totalSteps; i++) {
  var total = parseInt($("#total" + i).html());

  $("#progressbar" + i).progressbar({
    value: false,
    max: total,
  });
}

$(document).ready(function () {
  currentStep = 1;
  asyncDataImport();
});

function csrfSafeMethod(method) {
  // these HTTP methods do not require CSRF protection
  return /^(GET|HEAD|OPTIONS|TRACE)$/.test(method);
}

$.ajaxSetup({
  beforeSend(xhr, settings) {
    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader("X-CSRFToken", csrftoken);
    }
  },
});

const updateDomWithElementsProcessed = (elementsProcessed, uploadDone) => {
  if (uploadDone) {
    $("#total" + currentStep).html(elementsProcessed);
  }
  $("#offset" + currentStep).html(elementsProcessed);
  $("#progressbar" + currentStep).progressbar(
    "option",
    "value",
    elementsProcessed
  );
};

const handleUploadError = (error) => {
  alert(error);
  location.href = $("#tally_files_route").html();
}

const handleProceedToNextStep = () => {
  if (currentStep < totalSteps) {
    currentStep += 1;
    asyncDataImport();
  } else {
    location.href = $("#route_destination").html();
  }
}

const checkImportProgress = (taskId) => {
  $.ajax({
    url: $("#import-progress-url").html(),
    type: "POST",
    data: {
      step: currentStep,
      task_id: taskId
    },
    success(data) {
      if (data?.status === "OK") {
        if (data.elements_processed !== 0) {
          updateDomWithElementsProcessed(data?.elements_processed, data?.done);
        }
        if (data?.done === false) {
          checkImportProgress(taskId);
        } else {
          handleProceedToNextStep();
        }
      } else if (data?.status === "Error") {
        handleUploadError(data?.error_message);
      }
    }
  });
}

const asyncDataImport = () => {
  console.log({ currentStep });
  $.ajax({
    url: $("#route").html(),
    type: "POST",
    data: {
      offset: $("#offset" + currentStep).html(),
      step: currentStep,
    },
    success(data) {
      if (data?.status === "OK") {
        if (data?.elements_processed?.status === 'SUCCESS') {
          updateDomWithElementsProcessed(data?.elements_processed?.result, true);
          handleProceedToNextStep();
        } else if (data?.elements_processed?.status === 'FAILURE') {
          handleUploadError(data?.elements_processed?.result);
        } else if (data?.elements_processed?.status === 'PENDING') {
          setTimeout(checkImportProgress(data?.elements_processed?.task_id), 30000);
        }
      } else if (data?.status === "Error") {
        handleUploadError(data?.error_message);
      }
    },
  });
}
