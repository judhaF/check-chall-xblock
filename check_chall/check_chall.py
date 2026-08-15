from __future__ import absolute_import
from collections import Counter

import copy
import json
import logging
import re
import urllib.parse
import requests

import six
import webob
import html
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from xblock.fields import Boolean, Dict, Float, Integer, Scope, String
from xblock.scorable import ScorableXBlockMixin, Score
try:
    from xblock.utils.resources import ResourceLoader
    from xblock.utils.settings import ThemableXBlockMixin, XBlockWithSettingsMixin
    from xblock.utils.studio_editable import StudioEditableXBlockMixin
except ModuleNotFoundError:  # For backward compatibility with releases older than Quince.
    from xblockutils.resources import ResourceLoader
    from xblockutils.settings import ThemableXBlockMixin, XBlockWithSettingsMixin
    from xblockutils.studio_editable import StudioEditableXBlockMixin
from web_fragments.fragment import Fragment



loader = ResourceLoader(__name__)
logger = logging.getLogger(__name__)

@XBlock.wants('user')
class ExternalChallengeXBlock(    
    ScorableXBlockMixin,
    XBlock,
    XBlockWithSettingsMixin,
    ThemableXBlockMixin
):
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
        help="The full API URL to hit. ?email=student@example.com will be appended automatically."
    )

    expected_key = String(
        display_name="Response JSON Key",
        default="has_completed",
        scope=Scope.settings,
        help="The key in the API JSON response to inspect (e.g. 'has_completed', 'status', 'success')."
    )

    expected_value = String(
        display_name="Expected Success Value",
        default="true",
        scope=Scope.settings,
        help="The value that indicates completion (e.g. 'true', 'completed', 'passed', '1')."
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
        css_url = 'public/css/style.css'
        js_url = 'public/js/check_status.js'

        fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, js_url))
        fragment.initialize_js('ExternalChallengeXBlockInit')
        return fragment

    def author_view(self, context=None):
        """
        Fallback view rendered for course authors in Studio unit preview.
        """
        return self.student_view(context)

    def studio_view(self, context=None):
        """
        Editing view in Studio.
        
        ✅ FIXED: Use Fragment(html_content) directly instead of Fragment().add_content()
        """
        html_content = f"""<div class="wrapper-comp-settings edit-xblock-studio">
            <h2>Settings: External Challenge Verification</h2>
            <ul class="list-input settings-list" style="list-style: none; padding: 0;">
                <li class="field setting-point setting-item">
                    <label class="label setting-label" for="edit_display_name">Display Name</label>
                    <input class="input setting-input" type="text" id="edit_display_name" value="{html.escape(self.display_name, quote=True)}">
                    <span class="tip setting-help">Title of this component shown to students.</span>
                </li>
                <li class="field setting-point setting-item">
                    <label class="label setting-label" for="edit_api_url">Custom API Endpoint URL</label>
                    <input class="input setting-input" type="text" id="edit_api_url" value="{html.escape(self.api_url, quote=True)}">
                    <span class="tip setting-help">The API URL to hit. ?email=user@example.com will automatically be appended.</span>
                </li>
                <li class="field setting-point setting-item">
                    <label class="label setting-label" for="edit_expected_key">Response JSON Key</label>
                    <input class="input setting-input" type="text" id="edit_expected_key" value="{html.escape(self.expected_key, quote=True)}">
                    <span class="tip setting-help">The JSON key in the API response to evaluate.</span>
                </li>
                <li class="field setting-point setting-item">
                    <label class="label setting-label" for="edit_expected_value">Expected Success Value</label>
                    <input class="input setting-input" type="text" id="edit_expected_value" value="{html.escape(self.expected_value, quote=True)}">
                    <span class="tip setting-help">The value required for completion.</span>
                </li>
            </ul>
            <div class="xblock-actions actions">
                <ul>
                    <li class="action-item"><button type="button" class="action-primary save-button">Save</button></li>
                    <li class="action-item"><button type="button" class="button cancel-button">Cancel</button></li>
                </ul>
            </div>
        </div>"""

        # ✅ FIXED: Create Fragment with html_content directly
        fragment = Fragment(html_content)

        # Load resources
        css_url = 'public/css/style.css'
        js_url = 'public/js/studio_edit.js'

        fragment.add_css_url(self.runtime.local_resource_url(self, css_url))
        fragment.add_javascript_url(self.runtime.local_resource_url(self, js_url))

        # Pass explicit initial context object to JS init function
        fragment.initialize_js('ExternalChallengeStudioInit', {
            'display_name': self.display_name,
            'api_url': self.api_url,
            'expected_key': self.expected_key,
            'expected_value': self.expected_value,
        })

        return fragment

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Handler for saving author settings in Studio.
        """
        self.display_name = data.get('display_name', self.display_name)
        self.api_url = data.get('api_url', self.api_url)
        self.expected_key = data.get('expected_key', self.expected_key)
        self.expected_value = data.get('expected_value', self.expected_value)
        return {'result': 'success'}

    @XBlock.json_handler
    def verify_external_challenge(self, data, suffix=''):
        user_email = None

        # Safely retrieve student email via XBlock User Service
        user_service = self.runtime.service(self, 'user')
        if user_service:
            user = user_service.get_current_user()
            user_email = getattr(user, 'email', None)
        print(f"Masuk sini {user}")
        # Fallback for runtime environment
        if not user_email and hasattr(self.runtime, 'get_real_user') and hasattr(self.runtime, 'anonymous_student_id'):
            try:
                real_user = self.runtime.get_real_user(self.runtime.anonymous_student_id)
                user_email = getattr(real_user, 'email', None)
            except Exception:
                pass

        if not user_email:
            return {"success": False, "message": "Could not identify student email.: "}

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
        
    def has_submitted(self):
        return self.is_completed

    def calculate_score(self):
        score = 1.0 if self.is_completed else 0.0
        return Score(raw_earned=score, raw_possible=1.0)
    
    @staticmethod
    def workbench_scenarios():
        """
        Canned scenarios for display in the workbench.
        """
        return [
            (
                "External Challenge (Student View)",
                """<check_chall/>""",
            ),
            (
                "External Challenge (Studio Edit View)",
                """<check_chall view="studio_view"/>""",
            ),
        ]