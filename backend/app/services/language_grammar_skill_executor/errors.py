"""Skill Execution Framework errors (G3.4)."""

from __future__ import annotations


class SkillExecutorError(ValueError):
    """Invalid execution request, missing executor, or broken specification."""


class SkillExecutorDisabledError(SkillExecutorError):
    """Skill execution gated off by feature flags."""


class DuplicateExecutionIdError(SkillExecutorError):
    """execution_id already claimed in this guard scope."""


class MissingExecutorError(SkillExecutorError):
    """No registered executor supports the activity type."""


class BrokenSpecificationError(SkillExecutorError):
    """ActivitySpecification failed validation before execute."""
