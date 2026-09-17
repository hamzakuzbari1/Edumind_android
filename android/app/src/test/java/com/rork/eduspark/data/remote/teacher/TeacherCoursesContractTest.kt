package com.rork.eduspark.data.remote.teacher

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.float
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class TeacherCoursesContractTest {
    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    @Test
    fun createCourseJsonIncludesBackendRequiredFieldsEvenWhenDefaults() {
        val encoded = json.encodeToString(
            TeacherCourseCreateRequestDto(
                title = "رياضيات البكالوريا",
                description = "صف الرياضيات للصف الثاني عشر",
                subjectId = 4,
                grade = 12,
                price = 0f,
                currency = "SYP",
                isPublished = true,
            ),
        )
        val body = json.parseToJsonElement(encoded).jsonObject
        assertEquals("رياضيات البكالوريا", body.getValue("title").jsonPrimitive.content)
        assertEquals("صف الرياضيات للصف الثاني عشر", body.getValue("description").jsonPrimitive.content)
        assertEquals(4, body.getValue("subject_id").jsonPrimitive.int)
        assertEquals(12, body.getValue("grade").jsonPrimitive.int)
        assertEquals(0f, body.getValue("price").jsonPrimitive.float)
        assertEquals("SYP", body.getValue("currency").jsonPrimitive.content)
        assertEquals(true, body.getValue("is_published").jsonPrimitive.boolean)
        assertTrue("subjectId" !in body)
        assertTrue("isPublished" !in body)
    }
}
