from types import SimpleNamespace

import pytest

from app.services.routine_service import _generate_fast_routine_schedule, _validate_slots


class _EmptyScalarResult:
    def all(self):
        return []


class _EmptyExecuteResult:
    def scalars(self):
        return _EmptyScalarResult()


class _FakeDb:
    async def execute(self, *_args, **_kwargs):
        return _EmptyExecuteResult()


@pytest.mark.asyncio
async def test_fast_routine_schedule_builds_full_week_without_llm():
    profile = SimpleNamespace(
        student_id=123,
        grade_level="10",
        school_start="07:30",
        school_end="14:00",
        wake_time="06:30",
        sleep_time="22:30",
        school_days_json="[0,1,2,3,4]",
        activities_json='{"رياضة":true,"details":{"رياضة":{"days":[1],"start":"17:00","end":"18:00"}}}',
    )

    schedule = await _generate_fast_routine_schedule(
        _FakeDb(),
        profile,
        {"0": "أرجع من المدرسة، أرتاح، أدرس رياضيات، وعندي موعد عند الدكتور الساعة 18:00."},
        ["رياضيات"],
    )

    assert sorted(schedule.keys()) == [str(i) for i in range(7)]
    assert all(schedule[str(i)] for i in range(7))
    assert _validate_slots(schedule) == []
    assert any(slot.get("subject") == "رياضيات" for slots in schedule.values() for slot in slots)
    assert any(slot.get("type") == "school" for slot in schedule["0"])
    assert any(slot.get("type") == "sport" for slot in schedule["1"])
    assert any("موعد" in slot.get("title", "") for slot in schedule["0"])
