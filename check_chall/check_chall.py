from xblock.core import XBlock
from xblock.fields import Boolean, String, Scope
from xblock.fragment import Fragment
import requests

class ExternalChallengeXBlock(XBlock):
    has_score = True
    has_custom_completion = True

    display_name = String(
        display_name="Display Name",
        default="External Challenge Verification",
        scope=Scope.settings,
        help="Title of the component displayed to students."
    )

    api_url = String(
        display_name="API Endpoint URL",
        default="https://api.thirdparty.com/check-status",
        scope=Scope.settings,
        help="Custom 3rd-party API URL to hit for verifying student completion status."
    )

    expected_key = String(
        display_name="Response JSON Key",
        default="has_completed",
        scope=Scope.settings,
        help="The key in the API JSON response to inspect (e.g. 'has_completed', 'status')."
    )

    expected_value = String(
        display_name="Expected Success Value",
        default="true",
        scope=Scope.settings,
        help="The expected value indicating completion (e.g. 'true', 'completed', 'passed')."
    )

    is_completed = Boolean(
        default=False, 
        scope=Scope.user_state, 
        help="Tracks if student completed the external challenge"
    )

    def student_view(self, context=None):
        """
        Primary view shown to students in LMS and previewed in Studio.
        """
        html = f"""
        <div class="challenge-container">
            <h3>{self.display_name}</h3>
            <p>Click below to verify if you completed the challenge on the external platform.</p>
            <button class="check-challenge-btn">Verify Challenge Status</button>
            <div class="status-message"></div>
        </div>
        """
        fragment = Fragment(html)
        fragment.add_css_url(self.runtime.local_resource_url(self, "static/css/style.css"))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, "static/js/check_status.js"))
        fragment.initialize_js('ExternalChallengeXBlockInit')
        return fragment

    def author_view(self, context=None):
        """
        Fallback view rendered for course authors in Studio unit preview.
        """
        return self.student_view(context)

    @XBlock.json_handler
    def verify_external_challenge(self, data, suffix=''):
        user_email = None

        # Safely retrieve student email via XBlock User Service
        user_service = self.runtime.service(self, 'user')
        if user_service:
            user = user_service.get_current_user()
            user_email = getattr(user, 'email', None)

        # Fallback for runtime environment
        if not user_email and hasattr(self.runtime, 'get_real_user') and hasattr(self.runtime, 'anonymous_student_id'):
            try:
                real_user = self.runtime.get_real_user(self.runtime.anonymous_student_id)
                user_email = getattr(real_user, 'email', None)
            except Exception:
                pass

        if not user_email:
            return {"success": False, "message": "Could not identify student email."}

        # 1. Hit the custom 3rd-Party API URL configured by the lecturer
        try:
            sep = "&" if "?" in self.api_url else "?"
            url = f"{self.api_url}{sep}email={user_email}"
            response = requests.get(url, timeout=7)
            response_data = response.json()
        except Exception as e:
            return {"success": False, "message": f"Failed to connect to verification server ({self.api_url}): {str(e)}"}

        # 2. Inspect configured response key & expected value
        actual_val = response_data.get(self.expected_key)

        is_valid = False
        if str(actual_val).lower() == str(self.expected_value).lower():
            is_valid = True
        elif isinstance(actual_val, bool) and self.expected_value.lower() in ['true', 'false']:
            is_valid = (actual_val == (self.expected_value.lower() == 'true'))

        # 3. If response matches expected value, mark complete and publish 100% grade
        if is_valid:
            self.is_completed = True

            # Publish Grade & Completion to Open edX LMS
            self.runtime.publish(self, "grade", {
                "value": 1.0,
                "max_value": 1.0
            })
            self.runtime.publish(self, "completion", {
                "completion": 1.0
            })

            return {"success": True, "message": "Challenge verified! Course progress updated."}
        else:
            return {
                "success": False,
                "message": f"Challenge not completed yet on platform. Received '{self.expected_key}': '{actual_val}' (expected '{self.expected_value}')."
            }