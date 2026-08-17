/**
 * ExternalChallengeXBlock - Studio Edit JavaScript
 * 
 * PENTING: Function name HARUS match initialize_js() di Python:
 * Python: fragment.initialize_js('ExternalChallengeStudioInit', {...})
 * JavaScript: function ExternalChallengeStudioInit(runtime, element, initArgs) { ... }
 */

function ExternalChallengeStudioInit(runtime, element, initArgs) {
    'use strict';

    var $element = $(element);
    
    if (!element || $element.length === 0) {
        console.error('❌ xblockElement is empty or not defined');
        return;
    }

    console.log('✅ ExternalChallengeStudioInit loaded');

    // Cache form inputs
    var $displayNameInput = $('#edit_display_name', $element);
    var $apiUrlInput = $('#edit_api_url', $element);
    var $apiToken = $('#edit_api_token', $element);
    var $expectedKeyInput = $('#edit_expected_key', $element);
    var $expectedValueInput = $('#edit_expected_value', $element);
    var $saveBtn = $('.save-button', $element);
    var $cancelBtn = $('.cancel-button', $element);

    // Set initial values from initArgs
    if (initArgs) {
        if (initArgs.display_name) $displayNameInput.val(initArgs.display_name);
        if (initArgs.api_url) $apiUrlInput.val(initArgs.api_url);
        if (initArgs.api_token) $apiToken.val(initArgs.api_token);
        if (initArgs.expected_key) $expectedKeyInput.val(initArgs.expected_key);
        if (initArgs.expected_value) $expectedValueInput.val(initArgs.expected_value);
    }

    // Save button handler
    $saveBtn.on('click', function(e) {
        e.preventDefault();
        saveSettings();
    });

    // Cancel button handler
    $cancelBtn.on('click', function(e) {
        e.preventDefault();
        runtime.notify('cancel', {});
    });

    function saveSettings() {
        var data = {
            display_name: $displayNameInput.val(),
            api_url: $apiUrlInput.val(),
            api_token: $apiToken.val(),
            expected_key: $expectedKeyInput.val(),
            expected_value: $expectedValueInput.val(),
        };

        var handlerUrl = runtime.handlerUrl(element, 'studio_submit');

        $.ajax({
            type: 'POST',
            url: handlerUrl,
            data: JSON.stringify(data),
            dataType: 'json',
            success: function(response) {
                runtime.notify('save', {state: 'end'});
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error('Error saving:', errorThrown);
                runtime.notify('error', {});
            }
        });
    }
}