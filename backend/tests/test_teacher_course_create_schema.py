from app.schemas.teacher_courses import TeacherCourseCreate


def test_teacher_course_create_defaults_price_when_omitted():
    body = TeacherCourseCreate(title="رياضيات البكالوريا", subject_id=4, grade=12)
    assert body.price == 0
    assert body.currency == "SYP"
    assert body.is_published is True
    assert body.subject_id == 4
    assert body.grade == 12


def test_teacher_course_create_keeps_explicit_price_and_draft():
    body = TeacherCourseCreate(
        title="رياضيات البكالوريا",
        subject_id=4,
        grade=12,
        price=0,
        is_published=False,
        description="صف الرياضيات للصف الثاني عشر",
    )
    assert body.price == 0
    assert body.is_published is False
    assert body.description == "صف الرياضيات للصف الثاني عشر"
