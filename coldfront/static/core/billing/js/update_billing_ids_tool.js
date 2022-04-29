/**
 * TODO.
 */

$(document).ready(function() {

  // Run a function when the user stops typing.
  // Source: https://stackoverflow.com/a/4220182
  var doneTypingMs = 200;

  // Detect when the user stops typing in the updatedProjectId field.
  var updatedProjectIdTypingTimer;

  $('#updatedProjectId').on('keyup', function() {
    clearTimeout(updatedProjectIdTypingTimer);
    updatedProjectIdTypingTimer = setTimeout(validateProjectId, doneTypingMs);
  });

  $('#updatedProjectId').on('keydown', function() {
    clearTimeout(updatedProjectIdTypingTimer);
  });

  $('#applyActionForm').on('submit', function(event) {
    event.preventDefault();
    let action = $('#selectAction').find('option:selected').val();
    switch (action) {
      case 'find_and_replace':
        let findId = $('#currentProjectId').val();
        let replaceId = $('#updatedProjectId').val();
        findAndReplace(findId, replaceId);
      case 'set_to':
        let setId = $('#updatedProjectId').val();
        setTo(setId);
    }
  });

  $('#selectAction').change(function() {
    $('#findInput').toggle();
  });

  $('#selectAll').click(function() {
    let allSelected = $(this).prop('checked')
    let checkboxSelector = 'input[name^="update_ids_form-"]'
    $(checkboxSelector).prop('checked', allSelected);
  });

  function findAndReplace(findId, replaceId) {
    let selectedFormIds = new Set(getSelectedFormIds());
    let trSelector = '#updateUserFormsTable > tbody > tr';
    $(trSelector).each(function(index, tr) {
      if (selectedFormIds.has(index)) {
        let currentProjectId = $(tr).find('td:eq(4)').text();
        if (currentProjectId === findId) {
          $(`#id_update_ids_form-${index}-updated_billing_id`).val(replaceId);
        }
      }
    });
  }

  function getSelectedFormIds() {
    let checkboxSelector = 'input[name^="update_ids_form-"][type="checkbox"]'
    let ids = []
    $(checkboxSelector).each(function(index, input) {
      if (input.checked) {
        ids.push(index);
      }
    });
    return ids;
  }

  function setTo(setId) {
    let selectedFormIds = new Set(getSelectedFormIds());
    let trSelector = '#updateUserFormsTable > tbody > tr';
    $(trSelector).each(function(index, tr) {
      if (selectedFormIds.has(index)) {
        $(`#id_update_ids_form-${index}-updated_billing_id`).val(setId);
      }
    });
  }

  function validateProjectId() {

    let updatedProjectIdElement = document.getElementById('updatedProjectId');

    document.getElementById('validating-tooltip').style.display = 'none';
    updatedProjectIdElement.classList.remove('is-invalid');
    updatedProjectIdElement.classList.remove('is-valid');

    let updatedProjectId = updatedProjectIdElement.value;

    if (updatedProjectId.length === 0) {
      return;
    }

    const regex = new RegExp('^\\d{6}-\\d{3}$');
    if (!regex.test(updatedProjectId)) {
      updatedProjectIdElement.classList.add('is-invalid');
      return;
    }

    document.getElementById('validating-tooltip').style.display = '';

    let url = `/billing/is-billing-id-valid/${updatedProjectId}/`;
    axios.get(url)
      .then(response => {
        let data = response.data;
        let isValid = data.is_valid;
        document.getElementById('validating-tooltip').style.display = 'none';
        if (isValid) {
            updatedProjectIdElement.classList.add('is-valid');
        } else {
            updatedProjectIdElement.classList.add('is-invalid');
        }
      });
  }

});
