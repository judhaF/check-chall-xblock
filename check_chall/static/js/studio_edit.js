function ExternalChallengeStudioInit(runtime, element) {
    var handlerUrl = runtime.handlerUrl(element, 'studio_submit');

    $(element).find('.save-button').bind('click', function() {
        var data = {
            display_name: $(element).find('#edit_display_name').val(),
            api_url: $(element).find('#edit_api_url').val(),
            expected_key: $(element).find('#edit_expected_key').val(),
            expected_value: $(element).find('#edit_expected_value').val()
        };

        runtime.notify('save', {state: 'start'});
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify(data),
            contentType: "application/json",
            dataType: "json",
            success: function(response) {
                runtime.notify('save', {state: 'end'});
            },
            error: function() {
                runtime.notify('error', {msg: 'Failed to save settings'});
            }
        });
    });

    $(element).find('.cancel-button').bind('click', function() {
        runtime.notify('cancel', {});
    });
}
