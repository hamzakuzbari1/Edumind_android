## EduSpark Production PostgreSQL Architecture

This document describes the target production-grade schema and the migration strategy.

### Naming conventions

- **tables**: `snake_case`, plural nouns (`student_profiles`, `quiz_attempts`)
- **pk**: `id` (bigint recommended long-term)
- **fk**: `<entity>_id` (`teacher_profile_id`, `course_id`)
- **timestamps**: `created_at`, `updated_at`, optional `deleted_at` for soft delete
- **boolean flags**: `is_active`, `is_published`, `is_read`
- **enums**: PostgreSQL enum or string + check constraint (Alembic-managed)

### Core domains (ERD-style overview)

#### Auth & Users

- `users` (one row per account)
  - 1—1 `student_profiles` (optional)
  - 1—1 `teacher_profiles` (optional)
  - 1—many `notifications`

**Parent monitoring**
- `parent_student_links` links a parent `user_id` to a student `user_id`

#### Academic catalog

- `subjects` (grade-scoped)
- `teacher_profiles` owns teaching identity (bio/avatar/setup flags)
- `courses`
  - belongs to `teacher_profiles`
  - belongs to `subjects`
  - has many `lessons`

#### Lesson content (multi-asset)

- `lessons`
  - belongs to `courses`
  - `content_type`: `video|pdf|homework|ai`
  - supports multiple content rows by inserting multiple `lessons` for the same `course_id`

- `lesson_assets` — multiple assets per lesson (`video`, `pdf`, `homework`, `audio`, `image`, `attachment`)
  - `sort_order`, `mime_type`, `file_size_bytes`
  - FK `media_object_id` → `media_objects` (binary files never stored in PostgreSQL)

#### Media storage (provider-agnostic)

- `media_objects`: `storage_provider`, `storage_key`, `public_url`, `mime_type`, `file_size_bytes`
  - Providers: `local` today; `s3`, `r2`, `minio` later

#### Subscriptions & payments

- `student_course_access` is the **source of truth** for unlock state
  - one row per `(student_id, course_id)`
  - `payment_status` controls locking/unlocking
- `payments` + `payment_items` are append-only purchase history

#### Progress tracking

- `student_lesson_progress` records completions (idempotent unique `(student_id, lesson_id)`)

#### Quiz system

- `quiz_questions` belong to `lessons`
- `quiz_attempts` belong to `(lesson_id, student_id)`; aggregate analytics computed from attempts

#### Attendance

- `student_attendance_records` per student/day, used for monitoring + analytics

#### Notifications

- `notifications` (in-app + future multi-channel)
  - Types: `lesson_published`, `quiz_published`, `homework_assigned`, `homework_graded`, `payment_received`, `subscription_expiring`, `parent_alert`, `system_message`
  - `payload` JSONB for structured data; read/unread via `is_read`

#### Audit & sessions

- `audit_logs` — actor, entity, action, `old_values`/`new_values` JSONB, IP
- `auth_sessions` — refresh token hash, device metadata, revoke / logout-all support

#### Parent analytics (precomputed)

- `student_grade_reports` — per `(student_id, course_id)`: average_score, attendance %, completion %

#### Analytics rollups (no per-request aggregation)

- `course_analytics`, `teacher_analytics`, `student_analytics`
- Refresh via `analytics_rollup_service` (background job / cron)

#### AI processing queue

- `ai_jobs` — `pdf_chunking`, `embeddings`, `quiz_generation`, `chatbot_context_generation`, `voice_processing`
- Heavy work runs outside HTTP handlers; lesson PDF pipeline enqueues `ai_jobs`

#### Roles (backward compatible)

- `roles` + `user_roles` alongside legacy `users.role` column
- Slugs: `student`, `teacher`, `parent`, `admin`, `support`

### Avoiding circular FK problems

Rule: **A parent should not FK back to its children**.

Applied:
- Removed `courses.lesson_id` “primary lesson” link. `courses` owns a one-to-many to `lessons` only.

### Indexing strategy (baseline)

- `users(email)` unique
- `teacher_profiles(user_id)` unique
- `student_profiles(user_id)` unique
- `courses(teacher_profile_id, grade, subject_id)` composite (filtering + dashboards)
- `lessons(course_id, sort_order, id)` for ordered lesson lists
- `student_course_access(student_id, course_id)` unique + `(course_id, payment_status)`
- `student_lesson_progress(student_id, lesson_id)` unique + `(lesson_id)` for completion rates
- `quiz_attempts(student_id, lesson_id, created_at)`
- `student_attendance_records(student_id, date)` unique (already)
- `notifications(user_id, is_read, created_at)`

### Optimizations (production)

- Use **materialized views** or rollup tables for high-traffic analytics:
  - course completion %, most viewed, quiz averages
- Use **read replicas** for dashboards if needed
- Keep payment history append-only; never “update in place” except status transitions
- Prefer bigint IDs + partitioning for very large event tables (`activity_logs`, `quiz_attempts`)

### Migration strategy (mandatory)

1. **Stop** `create_all()` in startup (done).
2. **Disable** runtime patches in production: `APPLY_LEGACY_SCHEMA_PATCHES=false` (default).
3. Apply schema only via Alembic:
   ```bash
   cd backend
   alembic upgrade head
   ```
   Chain: `0001_baseline` → … → `0005_production_platform`
4. For existing DBs: backup first, then `alembic upgrade head` (migrations are idempotent where noted).
