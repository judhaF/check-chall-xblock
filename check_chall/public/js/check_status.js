window.ExternalChallengeXBlockInit = function(runtime, element) {
    var handlerUrl = runtime.handlerUrl(element, 'verify_external_challenge');
    var $button = $('.check-challenge-btn', element);
    var $statusMsg = $('.status-message', element);

    $button.click(function(eventObject) {
        $button.prop('disabled', true).text('Verifying...');
        $statusMsg.removeClass('success error').text('Checking status with external server...');
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify({}),
            contentType: "application/json",
            dataType: "json",
            success: function(response) {
                console.log(response)
                if (response.success) {
                    $statusMsg.removeClass('error').addClass('success').text(response.message);
                    $button.text('Verified').addClass('completed');
                } else {
                    $statusMsg.removeClass('success').addClass('error').text(response.message);
                    $button.prop('disabled', false).text('Verify Challenge Status');
                }
            },
            error: function() {
                $statusMsg.removeClass('success').addClass('error').text('An error occurred during verification. Please try again.');
                $button.prop('disabled', false).text('Verify Challenge Status');
            }
        });
    });
}
