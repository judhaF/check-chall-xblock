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
from xblock.fields import Boolean, Dict, Float, Integer, Scope, String, ScoreField
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
    ThemableXBlockMixin,
):
    """
    External Challenge XBlock - Verify student completion via external API
    """
    has_score = True
    icon_class = "problem"
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
    raw_earned = Float(
        scope=Scope.user_state,
        default=0,
        enforce_type=True,
    )

    raw_possible = Float(
        scope=Scope.user_state,
        default=1,
        enforce_type=True,
    )
    # Auto-generate studio edit form with these fields
    editable_fields = (
        'display_name',
        'api_url',
        'api_token',
        'expected_key',
        'expected_value',
    )

    @property
    def score(self):
        """
        Returns learners saved score.
        """
        return Score(self.raw_earned, self.raw_possible)

    def max_score(self):
        """
        Return the problem's max score, which for DnDv2 always equals 1.
        Required by the grading system in the LMS.
        """
        return 1

    def get_score(self):
        """
        Returns user's current (saved) score for the problem as raw values.
        """
        return Score(self.raw_earned, self.raw_possible)

    def set_score(self, score):
        """
        Sets the score on this block.
        Takes a Score namedtuple containing a raw
        score and possible max (for this block, we expect that this will
        always be 1).
        """
        self.raw_earned = score.raw_earned
        self.raw_possible = score.raw_possible

    def has_submitted_answer(self):
        """
        tells the gating engine if the student has attempted/completed this block.
        """
        return self.is_completed

    def student_view(self, context=None):
        """
        Primary view shown to students in LMS and previewed in Studio.
        """
        usage_id = str(self.scope_ids.usage_id)
        if not self.is_completed:
            html = f"""
            <div class="challenge-container" data-usage-id="{usage_id}" data-block-id="{usage_id}">
                <h3>{self.display_name}</h3>
                <p>Click below to verify if you completed the challenge on the external platform.</p>
                <button class="check-challenge-btn">Verify Challenge Status</button>
                <div class="status-message"></div>
            </div>
            """
        else:
            html = f"""
            <div class="challenge-container" data-usage-id="{usage_id}" data-block-id="{usage_id}">
                <h3>{self.display_name}</h3>
                <p class="completed-text">Completed !✅</p>
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

            # Publish grade event — this is what actually sets the grade in the LMS
            try:
                self.runtime.publish(self, "grade", {
                    "value": 1.0,
                    "max_value": 1.0,
                })
            except Exception as e:
                logger.warning(f"Failed to publish grade event: {e}")

            # Publish completion event
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

    def get_progress(self):
        """
        For now, just return weighted earned / weighted possible
        """
        if self.score:
            raw_earned = self.score.raw_earned
            raw_possible = self.score.raw_possible
        else:
            raw_earned = raw_possible = 0

        if raw_possible > 0:
            if self.weight is not None:
                # Progress objects expect total > 0
                if self.weight == 0:
                    return None

                # scale score and total by weight/total:
                weighted_earned = raw_earned * self.weight / raw_possible
                weighted_possible = self.weight
            else:
                weighted_earned = raw_earned
                weighted_possible = raw_possible
            try:
                return Progress(weighted_earned, weighted_possible)
            except (TypeError, ValueError):
                logger.exception("Got bad progress")
                return None
        return None
    
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