function ExternalChallengeStudioInit(runtime, element, data) {
    var $element = $(element);

    // Populate initial data if passed from Python context
    if (data) {
        if (data.display_name) { $element.find('#edit_display_name').val(data.display_name); }
        if (data.api_url) { $element.find('#edit_api_url').val(data.api_url); }
        if (data.expected_key) { $element.find('#edit_expected_key').val(data.expected_key); }
        if (data.expected_value) { $element.find('#edit_expected_value').val(data.expected_value); }
    }

    $element.find('.save-button').on('click', function(e) {
        e.preventDefault();

        var handlerUrl = runtime.handlerUrl(element, 'studio_submit');
        var payload = {
            display_name: $element.find('#edit_display_name').val(),
            api_url: $element.find('#edit_api_url').val(),
            expected_key: $element.find('#edit_expected_key').val(),
            expected_value: $element.find('#edit_expected_value').val()
        };

        if (runtime.notify) {
            runtime.notify('save', {state: 'start'});
        }

        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify(payload),
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            success: function(response) {
                if (runtime.notify) {
                    runtime.notify('save', {state: 'end'});
                }
            },
            error: function() {
                if (runtime.notify) {
                    runtime.notify('error', {message: 'Failed to save settings.'});
                }
            }
        });
    });

    $element.find('.cancel-button').on('click', function(e) {
        e.preventDefault();
        if (runtime.notify) {
            runtime.notify('cancel', {});
        }
    });
}