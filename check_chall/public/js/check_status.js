/**
 * ExternalChallengeXBlock - Student View JavaScript
 * 
 * PENTING: Function name HARUS match initialize_js() di Python:
 * Python: fragment.initialize_js('ExternalChallengeXBlockInit')
 * JavaScript: function ExternalChallengeXBlockInit(runtime, element, initArgs) { ... }
 */

function ExternalChallengeXBlockInit(runtime, element, initArgs) {
    'use strict';

    var $element = $(element);

    if (!element || $element.length === 0) {
        console.error('❌ xblockElement is empty or not defined');
        return;
    }

    console.log('✅ ExternalChallengeXBlockInit loaded');

    // Cache elements
    var $checkBtn = $('.check-challenge-btn', $element);
    var $statusMessage = $('.status-message', $element);

    // Get handler URL
    // Button click handler
    $checkBtn.on('click', function(e) {
        e.preventDefault();
        verifyChallenge();
    });
    
    function verifyChallenge() {
        var handlerUrl = runtime.handlerUrl(element, 'verify_external_challenge');
        console.log('Verifying challenge...');
        console.log(handlerUrl);

        // Show loading state
        $checkBtn.prop('disabled', true);
        $checkBtn.text('Verifying...');
        $statusMessage.html('').hide();

        $.ajax({
            type: 'POST',
            url: handlerUrl,
            data: JSON.stringify({}),
            dataType: 'json',
            success: function(response) {
                handleResponse(response);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error('Error:', errorThrown);
                showMessage('Error: ' + errorThrown, 'error');
            },
            complete: function() {
                $checkBtn.prop('disabled', false);
                $checkBtn.text('Verify Challenge Status');
            }
        });
    }

    function handleResponse(response) {
        console.log('Response:', response);

        if (response.success) {
            showMessage(response.message, 'success');
        } else {
            showMessage(response.message, 'error');
        }
    }

    function showMessage(message, type) {
        $statusMessage.removeClass('success error').addClass(type);
        $statusMessage.html(message).show();
    }
}