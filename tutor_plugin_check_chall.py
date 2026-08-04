from tutor import hooks

# In modern Tutor (v14+), use ENV_PATCHES to add extra pip requirements to openedx build.
# Note: 'ENV_REQUIREMENTS' was deprecated and removed in Tutor v14+.

hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-pip-requirements",
        "git+https://github.com/YOUR_GITHUB_USERNAME/check-chall-xblock.git"
    )
)
