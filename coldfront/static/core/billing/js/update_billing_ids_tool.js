/**
 * TODO.
 */

$(document).ready(function() {

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

});
