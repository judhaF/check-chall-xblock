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
        help="Name of this component shown in Studio and LMS"
    )

    api_url = String(
        display_name="API Endpoint URL",
        default="https://api.thirdparty.com/check-status",
        scope=Scope.settings,
        help="API URL to verify challenge status for student email"
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

    def studio_view(self, context=None):
        """
        View rendered when editing settings in Studio.
        """
        fragment = Fragment(f"""
        <div class="studio-xblock-wrapper">
            <h3>Edit {self.display_name}</h3>
            <p>This component checks student completion status via 3rd-party API: <code>{self.api_url}</code></p>
        </div>
        """)
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

        # 1. Hit the 3rd-Party API
        try:
            url = f"{self.api_url}?email={user_email}"
            response = requests.get(url, timeout=5)
            response_data = response.json()
        except Exception as e:
            return {"success": False, "message": f"Failed to connect to verification server: {str(e)}"}

        # 2. Check if the user completed the challenge
        if response_data.get("has_completed"):
            self.is_completed = True

            # 3. Publish Grade / Completion to Open edX LMS
            # Marking completed = 1.0 (100%) unlocks course progress
            self.runtime.publish(self, "grade", {
                "value": 1.0,
                "max_value": 1.0
            })
            self.runtime.publish(self, "completion", {
                "completion": 1.0
            })

            return {"success": True, "message": "Challenge verified! You may now proceed."}
        else:
            return {"success": False, "message": "Challenge not completed on the external platform yet."}