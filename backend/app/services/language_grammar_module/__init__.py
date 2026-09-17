"""Student Grammar Module — dashboard, generate-only start, Wave B completion surface.



Generate path never executes runtime, evaluates, or updates mastery/review.

Completion path delegates durable writes to the Grammar Pipeline orchestrator.

"""



from __future__ import annotations



from app.services.language_grammar_module.flags import grammar_module_enabled

from app.services.language_grammar_module.service import (

    build_grammar_dashboard,

    complete_grammar_activity,

    start_grammar_lesson,

)



PACKAGE_VERSION = "1.1.0"

RESPONSIBILITY = (

    "Student Grammar Module — dashboard + generate-only lesson start + "

    "Wave B activity completion (via pipeline Evidence→Mastery→Progression); "

    "never scores mastery or unlocks progression itself"

)



__all__ = [

    "PACKAGE_VERSION",

    "RESPONSIBILITY",

    "build_grammar_dashboard",

    "complete_grammar_activity",

    "grammar_module_enabled",

    "start_grammar_lesson",

]
