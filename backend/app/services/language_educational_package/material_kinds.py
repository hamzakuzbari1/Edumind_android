"""Input material kinds — format-agnostic educational inputs."""

from __future__ import annotations

from enum import StrEnum


class InputMaterialKind(StrEnum):
    story = "story"
    dialogue = "dialogue"
    email = "email"
    advertisement = "advertisement"
    restaurant_menu = "restaurant_menu"
    whatsapp = "whatsapp"
    news_article = "news_article"
    blog = "blog"
    airport_announcement = "airport_announcement"
    travel_brochure = "travel_brochure"
    instructions = "instructions"
    conversation_transcript = "conversation_transcript"
    custom = "custom"


class BodyBlockKind(StrEnum):
    paragraph = "paragraph"
    turn = "turn"
    menu_item = "menu_item"
    message = "message"
    heading = "heading"
    list_item = "list_item"
    other = "other"
