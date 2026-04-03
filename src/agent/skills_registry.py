from __future__ import annotations

from src.agent.skills_manifest import SKILLS, SkillManifest


class SkillsRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, SkillManifest] = {s.skill_id: s for s in SKILLS}

    def get_skill(self, skill_id: str) -> SkillManifest:
        return self._registry[skill_id]  # raises KeyError if not found

    def list_skills(self) -> list[SkillManifest]:
        return sorted(self._registry.values(), key=lambda s: s.priority)


_registry: SkillsRegistry | None = None


def get_registry() -> SkillsRegistry:
    global _registry
    if _registry is None:
        _registry = SkillsRegistry()
    return _registry
