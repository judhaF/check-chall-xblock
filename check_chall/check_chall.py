from xblock.core import XBlock
from xblock.fields import Boolean, Scope
from xblock.fragment import Fragment
import requests

class ExternalChallengeXBlock(XBlock):
    has_score = True
    has_custom_completion = True

    is_completed = Boolean(
        default=False, 
        scope=Scope.user_state, 
        help="Tracks if student completed the external challenge"
    )

    def student_view(self, context=None):
        html = f"""
        <div class="challenge-container">
            <h3>External Challenge Verification</h3>
            <p>Click below to verify if you completed the challenge on Platform X.</p>
            <button class="check-challenge-btn">Verify Challenge Status</button>
            <div class="status-message"></div>
        </div>
        """
        fragment = Fragment(html)
        fragment.add_css_url(self.runtime.local_resource_url(self, "static/css/style.css"))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, "static/js/check_status.js"))
        fragment.initialize_js('ExternalChallengeXBlockInit')
        return fragment

    @XBlock.json_handler
    def verify_external_challenge(self, data, suffix=''):
        user_email = self.runtime.get_real_user(self.runtime.anonymous_student_id).email
        
        # 1. Hit the 3rd-Party API
        try:
            api_url = f"https://api.thirdparty.com/check-status?email={user_email}"
            response = requests.get(api_url, timeout=5)
            response_data = response.json()
        except Exception:
            return {"success": False, "message": "Failed to connect to verification server."}

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