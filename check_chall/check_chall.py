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
    StudioEditableXBlockMixin,
    XBlockWithSettingsMixin,
    ThemableXBlockMixin
):
    """
    External Challenge XBlock - Verify student completion via external API
    """
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
        help="The full API URL to hit. {username} will be changed to session username."
    )

    api_token = String(
        display_name="API Endpoint Bearer Token",
        scope=Scope.settings,
        help="The full API bearer token"
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

    # Auto-generate studio edit form with these fields
    editable_fields = (
        'display_name',
        'api_url',
        'api_token',
        'expected_key',
        'expected_value',
    )

    def student_view(self, context=None):
        """
        Primary view shown to students in LMS and previewed in Studio.
        """
        usage_id = str(self.scope_ids.usage_id)
        html = f"""
        <div class="challenge-container" data-usage-id="{usage_id}" data-block-id="{usage_id}">
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
        """
        Handler to verify student completion status via external API
        """
        username = None

        # Safely retrieve student email via XBlock User Service
        try:
            user_service = self.runtime.service(self, 'user')
            if user_service:
                user = user_service.get_current_user()
                username = getattr(user, 'username', None)
        except Exception as e:
            logger.info(f"User service lookup error: {e}")

        # 2. Fallback for Open edX LMS runtime environment
        if not username and hasattr(self.runtime, 'get_real_user') and hasattr(self.runtime, 'anonymous_student_id'):
            try:
                real_user = self.runtime.get_real_user(self.runtime.anonymous_student_id)
                username = getattr(real_user, 'username', None)
            except Exception:
                pass
        
        if not username:
            return {"success": False, "message": "Could not identify student username."}

        if "{username}" in self.api_url:
            url = self.api_url.replace("{username}", username)
        else:
            sep = "&" if "?" in self.api_url else "?"
            url = f"{self.api_url}{sep}username={username}"
        header = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=header, timeout=7)
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

            try:
                score = Score(raw_earned=1.0, raw_possible=1.0)
                self.set_score(score)
            except Exception as e:
                logger.warning(f"Failed to set_score: {e}")

            # Publish completion event safely
            try:
                self.runtime.publish(self, "completion", {"completion": 1.0})
            except Exception as e:
                logger.warning(f"Failed to publish completion event: {e}")

            try:
                self.runtime.publish(self, "completion", {"completion": 1.0})
            except Exception as e:
                logger.warning(f"Failed to publish completion event: {e}")
            
            return {"success": True, "message": "Challenge verified! Course progress updated."}
        else:
            return {
                "url":url,
                "success": False,
                "message": f"Challenge not completed yet."
            }
        
    def has_submitted(self):
        """
        Returns True if student has completed the challenge
        """
        return self.is_completed

    def calculate_score(self):
        """
        Calculate the score for this XBlock
        """
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