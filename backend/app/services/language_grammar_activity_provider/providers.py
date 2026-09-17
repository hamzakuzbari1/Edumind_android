"""Concrete activity providers (G3.35.1) — return ActivitySpecification only."""

from __future__ import annotations

from app.services.language_grammar_activity_provider.spec_factory import build_activity_specification
from app.services.language_grammar_activity_provider.types import (
    ActivityExecutionContext,
    GrammarActivityProviderId,
)
from app.services.language_grammar_activity_spec import ActivitySpecification


class TemplateProvider:
    """Deterministic template activity — default production provider."""

    provider_id = GrammarActivityProviderId.template

    def supports(self, context: ActivityExecutionContext) -> bool:
        return True

    def provide(self, context: ActivityExecutionContext) -> ActivitySpecification:
        step = context.step
        goal = context.blueprint.lesson_goal or (
            context.blueprint.objectives[0] if context.blueprint.objectives else step.kind.value
        )
        instructions = (
            f"Template activity for {step.kind.value} on {context.blueprint.grammar_id}. "
            f"Goal: {goal}."
        )
        if step.context_hint:
            instructions = f"{instructions} Context: {step.context_hint}."
        return build_activity_specification(
            context,
            provider_id=self.provider_id,
            title=step.title or f"Template {step.kind.value}",
            goal=goal,
            instructions=instructions,
            generation_mode="template",
            cacheable=True,
        )


class CachedProvider:
    """Cache-shaped provider — deterministic cached shell (no I/O)."""

    provider_id = GrammarActivityProviderId.cached

    def supports(self, context: ActivityExecutionContext) -> bool:
        return True

    def provide(self, context: ActivityExecutionContext) -> ActivitySpecification:
        step = context.step
        goal = context.blueprint.lesson_goal or step.kind.value
        instructions = (
            f"Cached activity shell for {step.step_id} "
            f"(fingerprint={context.blueprint.fingerprint})."
        )
        return build_activity_specification(
            context,
            provider_id=self.provider_id,
            title=step.title or f"Cached {step.kind.value}",
            goal=goal,
            instructions=instructions,
            generation_mode="cached",
            cacheable=True,
        )


class ClaudeProvider:
    """Stub Claude provider — does NOT call Claude APIs."""

    provider_id = GrammarActivityProviderId.claude

    def supports(self, context: ActivityExecutionContext) -> bool:
        return True

    def provide(self, context: ActivityExecutionContext) -> ActivitySpecification:
        step = context.step
        goal = context.blueprint.lesson_goal or step.kind.value
        return build_activity_specification(
            context,
            provider_id=self.provider_id,
            title=step.title or f"Claude stub {step.kind.value}",
            goal=goal,
            instructions="ClaudeProvider stub — no API call.",
            prompt_stub="[deferred:claude_prompt_not_generated]",
            generation_mode="claude_stub",
            cacheable=False,
        )


class FutureLLMProvider:
    """Stub future-LLM provider — swap-in without Runtime redesign."""

    provider_id = GrammarActivityProviderId.future_llm

    def supports(self, context: ActivityExecutionContext) -> bool:
        return True

    def provide(self, context: ActivityExecutionContext) -> ActivitySpecification:
        step = context.step
        goal = context.blueprint.lesson_goal or step.kind.value
        return build_activity_specification(
            context,
            provider_id=self.provider_id,
            title=step.title or f"FutureLLM stub {step.kind.value}",
            goal=goal,
            instructions="FutureLLMProvider stub — no LLM call.",
            prompt_stub="[deferred:future_llm_prompt_not_generated]",
            generation_mode="future_llm_stub",
            cacheable=False,
        )
