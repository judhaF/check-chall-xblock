window.ExternalChallengeXBlockStudioInit = function(runtime, element) {
    var $element = $(element);

    $element.find('.save-button').on('click', function(e) {
        e.preventDefault();

        var handlerUrl = runtime.handlerUrl(element, 'studio_submit');
        var data = {
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
            data: JSON.stringify(data),
            contentType: "application/json; charset=utf-8",
            dataType: "json",
            success: function(response) {
                if (runtime.notify) {
                    runtime.notify('save', {state: 'end'});
                } else {
                    alert('Settings saved successfully!');
                }
            },
            error: function() {
                alert('Failed to save settings.');
            }
        });
    });

    $element.find('.cancel-button').on('click', function(e) {
        e.preventDefault();
        if (runtime.notify) {
            runtime.notify('cancel', {});
        }
    });
};