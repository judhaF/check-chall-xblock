import os
from setuptools import setup

def package_data(pkg, roots):
    """Generic function to find all static/template files in subdirectories."""
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))
    return {pkg: data}

setup(
    name='check-chall-xblock',
    version='0.1.0',
    description='XBlock that verifies external challenge completion',
    packages=[
        'check_chall',
    ],
    install_requires=[
        'XBlock',
        'requests',  # Add any external Python dependencies here
    ],
    # IMPORTANT: This entry point tells Open edX that this package contains an XBlock
    entry_points={
        'xblock.v1': [
            'check_chall = check_chall:ExternalChallengeXBlock',
        ],
    },
    # Includes all CSS, JS, HTML, and image static files in the Python build package
    package_data=package_data("check_chall", ["static", "public"]),
)