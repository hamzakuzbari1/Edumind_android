--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: activityeventtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.activityeventtype AS ENUM (
    'quiz_submitted',
    'study_session_completed',
    'study_streak',
    'no_study_today',
    'planner_generated',
    'weak_subject_alert',
    'lesson_activity',
    'performance_improved',
    'weekly_summary'
);


--
-- Name: activitysessionlogoutreason; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.activitysessionlogoutreason AS ENUM (
    'logout',
    'expired',
    'inactivity'
);


--
-- Name: attendancestatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.attendancestatus AS ENUM (
    'present',
    'absent',
    'partial'
);


--
-- Name: engagementeventtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.engagementeventtype AS ENUM (
    'login',
    'logout',
    'session_expired',
    'session_inactive',
    'lesson_opened',
    'lesson_viewed',
    'lesson_completed',
    'quiz_started',
    'quiz_submitted',
    'planner_activity',
    'messaging_activity',
    'page_navigation'
);


--
-- Name: language_content_progress_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language_content_progress_status AS ENUM (
    'not_started',
    'in_progress',
    'completed'
);


--
-- Name: language_level; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language_level AS ENUM (
    'A1',
    'A2',
    'B1',
    'B2',
    'C1',
    'C2'
);


--
-- Name: language_onboarding_step; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language_onboarding_step AS ENUM (
    'select_language',
    'placement',
    'dashboard'
);


--
-- Name: language_placement_attempt_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language_placement_attempt_status AS ENUM (
    'in_progress',
    'submitted',
    'abandoned'
);


--
-- Name: language_skill; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language_skill AS ENUM (
    'reading',
    'listening',
    'writing',
    'speaking'
);


--
-- Name: language_vocabulary_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language_vocabulary_status AS ENUM (
    'new',
    'learning',
    'known'
);


--
-- Name: lessonassettype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.lessonassettype AS ENUM (
    'video',
    'pdf',
    'homework',
    'audio',
    'image',
    'attachment'
);


--
-- Name: lessoncontenttype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.lessoncontenttype AS ENUM (
    'video',
    'pdf',
    'homework',
    'ai'
);


--
-- Name: lessonstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.lessonstatus AS ENUM (
    'draft',
    'processing',
    'processed',
    'error'
);


--
-- Name: lifeeventtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.lifeeventtype AS ENUM (
    'school',
    'private_lesson',
    'exam',
    'sport',
    'family',
    'social',
    'religious',
    'other'
);


--
-- Name: notificationchannel; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notificationchannel AS ENUM (
    'in_app',
    'email',
    'sms',
    'whatsapp'
);


--
-- Name: onboardingstep; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.onboardingstep AS ENUM (
    'grade',
    'subjects',
    'teachers',
    'complete'
);


--
-- Name: payment_item_product_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.payment_item_product_type AS ENUM (
    'course',
    'language'
);


--
-- Name: paymentmethod; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.paymentmethod AS ENUM (
    'card',
    'transfer',
    'wallet',
    'cash'
);


--
-- Name: paymentstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.paymentstatus AS ENUM (
    'pending',
    'paid',
    'failed'
);


--
-- Name: scheduleslotstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.scheduleslotstatus AS ENUM (
    'planned',
    'completed',
    'missed'
);


--
-- Name: userrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userrole AS ENUM (
    'teacher',
    'student'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_jobs (
    id integer NOT NULL,
    job_type character varying(64) NOT NULL,
    status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    lesson_id integer,
    payload jsonb,
    result jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);


--
-- Name: ai_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ai_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ai_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ai_jobs_id_seq OWNED BY public.ai_jobs.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    actor_user_id integer,
    entity_type character varying(64) NOT NULL,
    entity_id integer,
    action character varying(64) NOT NULL,
    old_values jsonb,
    new_values jsonb,
    ip_address character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- Name: auth_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_sessions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    refresh_token_hash character varying(255) NOT NULL,
    device_name character varying(120),
    device_type character varying(32),
    ip_address character varying(64),
    user_agent text,
    last_seen_at timestamp with time zone,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: auth_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_sessions_id_seq OWNED BY public.auth_sessions.id;


--
-- Name: availability_blocks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.availability_blocks (
    id integer NOT NULL,
    student_id integer NOT NULL,
    day_of_week integer NOT NULL,
    start_time time without time zone NOT NULL,
    end_time time without time zone NOT NULL,
    label character varying(20) NOT NULL,
    is_recurring boolean NOT NULL,
    notes character varying(255)
);


--
-- Name: availability_blocks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.availability_blocks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: availability_blocks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.availability_blocks_id_seq OWNED BY public.availability_blocks.id;


--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_messages (
    id integer NOT NULL,
    lesson_id integer NOT NULL,
    student_id integer NOT NULL,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chat_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chat_messages_id_seq OWNED BY public.chat_messages.id;


--
-- Name: content_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.content_chunks (
    id integer NOT NULL,
    lesson_id integer NOT NULL,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    metadata_json text
);


--
-- Name: content_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.content_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: content_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.content_chunks_id_seq OWNED BY public.content_chunks.id;


--
-- Name: conversation_message_reads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_message_reads (
    id integer NOT NULL,
    message_id integer NOT NULL,
    user_id integer NOT NULL,
    read_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: conversation_message_reads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conversation_message_reads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_message_reads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conversation_message_reads_id_seq OWNED BY public.conversation_message_reads.id;


--
-- Name: conversation_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_messages (
    id integer NOT NULL,
    thread_id integer NOT NULL,
    sender_id integer NOT NULL,
    body text NOT NULL,
    status character varying(16) DEFAULT 'sent'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    message_kind character varying(24) DEFAULT 'text'::character varying NOT NULL,
    attachment_url character varying(512),
    attachment_name character varying(255),
    attachment_mime character varying(128),
    voice_duration_ms integer,
    deleted_at timestamp with time zone
);


--
-- Name: conversation_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conversation_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conversation_messages_id_seq OWNED BY public.conversation_messages.id;


--
-- Name: conversation_participants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_participants (
    id integer NOT NULL,
    thread_id integer NOT NULL,
    user_id integer NOT NULL,
    role character varying(16) NOT NULL,
    last_read_at timestamp with time zone,
    joined_at timestamp with time zone DEFAULT now() NOT NULL,
    is_pinned boolean DEFAULT false NOT NULL,
    is_archived boolean DEFAULT false NOT NULL
);


--
-- Name: conversation_participants_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conversation_participants_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_participants_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conversation_participants_id_seq OWNED BY public.conversation_participants.id;


--
-- Name: conversation_threads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_threads (
    id integer NOT NULL,
    title character varying(255),
    thread_type character varying(32) NOT NULL,
    student_id integer NOT NULL,
    created_by_user_id integer NOT NULL,
    last_message_at timestamp with time zone,
    last_message_preview character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    course_id integer,
    include_parent boolean DEFAULT false NOT NULL,
    teacher_user_id integer,
    parent_user_id integer
);


--
-- Name: conversation_threads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conversation_threads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conversation_threads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conversation_threads_id_seq OWNED BY public.conversation_threads.id;


--
-- Name: course_analytics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_analytics (
    course_id integer NOT NULL,
    student_count integer DEFAULT 0 NOT NULL,
    completion_rate double precision DEFAULT '0'::double precision NOT NULL,
    average_quiz_score double precision,
    active_students integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: course_quiz_answers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_quiz_answers (
    id integer NOT NULL,
    attempt_id integer NOT NULL,
    question_id integer NOT NULL,
    answer_json text,
    points_earned double precision,
    is_correct boolean,
    teacher_feedback text,
    graded_at timestamp with time zone,
    graded_by_user_id integer
);


--
-- Name: course_quiz_answers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_quiz_answers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_quiz_answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_quiz_answers_id_seq OWNED BY public.course_quiz_answers.id;


--
-- Name: course_quiz_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_quiz_attempts (
    id integer NOT NULL,
    quiz_id integer NOT NULL,
    student_id integer NOT NULL,
    status character varying(32) DEFAULT 'in_progress'::character varying NOT NULL,
    score double precision DEFAULT 0 NOT NULL,
    max_score double precision DEFAULT 0 NOT NULL,
    percent double precision,
    passed boolean,
    started_at timestamp with time zone DEFAULT now(),
    submitted_at timestamp with time zone,
    graded_at timestamp with time zone
);


--
-- Name: course_quiz_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_quiz_attempts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_quiz_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_quiz_attempts_id_seq OWNED BY public.course_quiz_attempts.id;


--
-- Name: course_quiz_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_quiz_questions (
    id integer NOT NULL,
    quiz_id integer NOT NULL,
    question_type character varying(32) NOT NULL,
    question_text text NOT NULL,
    options_json text,
    correct_answer_json text,
    points integer DEFAULT 1 NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    requires_manual_grading boolean DEFAULT false NOT NULL
);


--
-- Name: course_quiz_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_quiz_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_quiz_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_quiz_questions_id_seq OWNED BY public.course_quiz_questions.id;


--
-- Name: course_quizzes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.course_quizzes (
    id integer NOT NULL,
    course_id integer NOT NULL,
    title character varying(500) NOT NULL,
    description text,
    duration_minutes integer,
    passing_score_percent integer DEFAULT 60 NOT NULL,
    is_published boolean DEFAULT false NOT NULL,
    due_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: course_quizzes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.course_quizzes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: course_quizzes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.course_quizzes_id_seq OWNED BY public.course_quizzes.id;


--
-- Name: courses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.courses (
    id integer NOT NULL,
    title character varying(500) NOT NULL,
    subject_id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    grade integer NOT NULL,
    price double precision NOT NULL,
    currency character varying(10) NOT NULL,
    is_active boolean NOT NULL,
    lesson_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    description text,
    is_published boolean DEFAULT true,
    thumbnail_url character varying(1024),
    banner_url character varying(1024)
);


--
-- Name: courses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.courses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: courses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.courses_id_seq OWNED BY public.courses.id;


--
-- Name: email_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token_hash character varying(64) NOT NULL,
    purpose character varying(32) DEFAULT 'verification'::character varying NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: email_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.email_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.email_tokens_id_seq OWNED BY public.email_tokens.id;


--
-- Name: exams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.exams (
    id integer NOT NULL,
    student_id integer NOT NULL,
    subject character varying(120) NOT NULL,
    title character varying(255) NOT NULL,
    exam_at timestamp with time zone NOT NULL,
    priority integer NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: exams_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.exams_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: exams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.exams_id_seq OWNED BY public.exams.id;


--
-- Name: language_activity_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_activity_log (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    event_type character varying(64) NOT NULL,
    skill public.language_skill,
    duration_seconds integer DEFAULT 0 NOT NULL,
    payload_json jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_activity_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_activity_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_activity_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_activity_log_id_seq OWNED BY public.language_activity_log.id;


--
-- Name: language_ai_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_ai_usage (
    id integer NOT NULL,
    operation character varying(100) DEFAULT ''::character varying NOT NULL,
    model character varying(80) DEFAULT ''::character varying NOT NULL,
    input_tokens integer DEFAULT 0 NOT NULL,
    output_tokens integer DEFAULT 0 NOT NULL,
    total_tokens integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_ai_usage_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_ai_usage_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_ai_usage_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_ai_usage_id_seq OWNED BY public.language_ai_usage.id;


--
-- Name: language_analytics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_analytics (
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    reading_level public.language_level,
    listening_level public.language_level,
    writing_level public.language_level,
    speaking_level public.language_level,
    overall_level_internal public.language_level,
    primary_focus_skill character varying(32),
    strength_skill character varying(32),
    vocabulary_count integer DEFAULT 0 NOT NULL,
    estimated_time_to_next_level character varying(64),
    target_progress_percent integer,
    weekly_minutes_json jsonb,
    skill_growth_json jsonb,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    statistics_json jsonb
);


--
-- Name: language_assessment_skill_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_assessment_skill_scores (
    id integer NOT NULL,
    assessment_id integer NOT NULL,
    skill public.language_skill NOT NULL,
    score_percent double precision DEFAULT 0 NOT NULL,
    level public.language_level NOT NULL,
    raw_metrics_json jsonb,
    ai_evaluation_json jsonb
);


--
-- Name: language_assessment_skill_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_assessment_skill_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_assessment_skill_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_assessment_skill_scores_id_seq OWNED BY public.language_assessment_skill_scores.id;


--
-- Name: language_assessments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_assessments (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    attempt_id integer NOT NULL,
    overall_level public.language_level,
    overall_calculation_method character varying(32) DEFAULT 'bottleneck'::character varying NOT NULL,
    completed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_assessments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_assessments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_assessments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_assessments_id_seq OWNED BY public.language_assessments.id;


--
-- Name: language_certificates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_certificates (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    certificate_level public.language_level NOT NULL,
    certificate_number character varying(64) NOT NULL,
    verification_code character varying(64) NOT NULL,
    certificate_status character varying(32) DEFAULT 'issued'::character varying NOT NULL,
    verification_url character varying(2048),
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    pdf_url character varying(2048)
);


--
-- Name: language_certificates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_certificates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_certificates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_certificates_id_seq OWNED BY public.language_certificates.id;


--
-- Name: language_component_mastery; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_component_mastery (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    component_id integer NOT NULL,
    p_mastery double precision DEFAULT '0.1'::double precision NOT NULL,
    confidence double precision DEFAULT '0'::double precision NOT NULL,
    evidence_count integer DEFAULT 0 NOT NULL,
    ease_factor double precision DEFAULT '2.5'::double precision NOT NULL,
    interval_days integer DEFAULT 1 NOT NULL,
    repetition_number integer DEFAULT 0 NOT NULL,
    next_review_at timestamp with time zone,
    last_seen_at timestamp with time zone,
    source_weight double precision DEFAULT '1'::double precision NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_component_mastery_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_component_mastery_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_component_mastery_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_component_mastery_id_seq OWNED BY public.language_component_mastery.id;


--
-- Name: language_content_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_content_items (
    id integer NOT NULL,
    language_id integer NOT NULL,
    skill public.language_skill NOT NULL,
    level public.language_level NOT NULL,
    content_type character varying(32) DEFAULT 'lesson'::character varying NOT NULL,
    title character varying(500) NOT NULL,
    body_json jsonb,
    media_object_id integer,
    sort_order integer DEFAULT 0 NOT NULL,
    is_published boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_content_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_content_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_content_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_content_items_id_seq OWNED BY public.language_content_items.id;


--
-- Name: language_conversation_scenarios; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_conversation_scenarios (
    id integer NOT NULL,
    language_id integer NOT NULL,
    scenario_key character varying(64) NOT NULL,
    title_en character varying(200) NOT NULL,
    title_ar character varying(200) NOT NULL,
    description_en text,
    description_ar text,
    level_min public.language_level NOT NULL,
    ai_role character varying(200) NOT NULL,
    student_role character varying(200) NOT NULL,
    opening_line text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    category character varying(32) DEFAULT 'daily_conversation'::character varying NOT NULL,
    target_skills_json jsonb DEFAULT '[]'::jsonb NOT NULL
);


--
-- Name: language_conversation_scenarios_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_conversation_scenarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_conversation_scenarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_conversation_scenarios_id_seq OWNED BY public.language_conversation_scenarios.id;


--
-- Name: language_curriculum_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_curriculum_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    objective_id character varying(48) NOT NULL,
    status character varying(16) DEFAULT 'new'::character varying NOT NULL,
    practice_count integer DEFAULT 0 NOT NULL,
    last_practiced_at timestamp with time zone,
    mastered_at timestamp with time zone
);


--
-- Name: language_curriculum_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_curriculum_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_curriculum_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_curriculum_progress_id_seq OWNED BY public.language_curriculum_progress.id;


--
-- Name: language_error_patterns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_error_patterns (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    error_type character varying(20) NOT NULL,
    pattern_key character varying(200) NOT NULL,
    incorrect_form text NOT NULL,
    corrected_form text DEFAULT ''::text NOT NULL,
    context_sentence text,
    occurrence_count integer DEFAULT 1 NOT NULL,
    first_seen timestamp with time zone DEFAULT now() NOT NULL,
    last_seen timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_error_patterns_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_error_patterns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_error_patterns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_error_patterns_id_seq OWNED BY public.language_error_patterns.id;


--
-- Name: language_exam_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_exam_sessions (
    id character varying(32) NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    current_step integer DEFAULT 1 NOT NULL,
    max_steps integer DEFAULT 6 NOT NULL,
    scenario_json jsonb,
    chat_history jsonb,
    exam_state jsonb,
    status character varying(20) DEFAULT 'in_progress'::character varying NOT NULL,
    is_completed boolean DEFAULT false NOT NULL,
    assessment_report jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone
);


--
-- Name: language_generated_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_generated_questions (
    id integer NOT NULL,
    language_id integer NOT NULL,
    component_code character varying(64) NOT NULL,
    display_skill public.language_skill NOT NULL,
    cefr_level public.language_level NOT NULL,
    question_type character varying(32) DEFAULT 'mcq'::character varying NOT NULL,
    prompt_json jsonb NOT NULL,
    source character varying(16) DEFAULT 'placement'::character varying NOT NULL,
    verified boolean DEFAULT false NOT NULL,
    verification_note character varying(400),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_generated_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_generated_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_generated_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_generated_questions_id_seq OWNED BY public.language_generated_questions.id;


--
-- Name: language_knowledge_components; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_knowledge_components (
    id integer NOT NULL,
    code character varying(64) NOT NULL,
    display_skill public.language_skill NOT NULL,
    category character varying(32) NOT NULL,
    cefr_level public.language_level NOT NULL,
    prerequisites jsonb,
    title character varying(200),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_knowledge_components_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_knowledge_components_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_knowledge_components_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_knowledge_components_id_seq OWNED BY public.language_knowledge_components.id;


--
-- Name: language_learning_paths; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_learning_paths (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    assessment_id integer,
    overall_level public.language_level,
    path_json jsonb DEFAULT '{}'::jsonb NOT NULL,
    generated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_learning_paths_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_learning_paths_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_learning_paths_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_learning_paths_id_seq OWNED BY public.language_learning_paths.id;


--
-- Name: language_lesson_audio_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_lesson_audio_cache (
    id integer NOT NULL,
    content_item_id integer NOT NULL,
    voice_source character varying(32) NOT NULL,
    teacher_id integer,
    audio_storage_key character varying(1024) NOT NULL,
    public_url character varying(2048) NOT NULL,
    duration_seconds integer,
    generated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_lesson_audio_cache_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_lesson_audio_cache_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_lesson_audio_cache_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_lesson_audio_cache_id_seq OWNED BY public.language_lesson_audio_cache.id;


--
-- Name: language_listening_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_listening_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    content_item_id integer NOT NULL,
    status public.language_content_progress_status DEFAULT 'not_started'::public.language_content_progress_status NOT NULL,
    score_percent double precision,
    completed_at timestamp with time zone,
    attempt_count integer DEFAULT 0 NOT NULL
);


--
-- Name: language_listening_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_listening_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_listening_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_listening_progress_id_seq OWNED BY public.language_listening_progress.id;


--
-- Name: language_path_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_path_items (
    id integer NOT NULL,
    path_id integer NOT NULL,
    skill public.language_skill NOT NULL,
    level public.language_level NOT NULL,
    content_item_id integer,
    sort_order integer DEFAULT 0 NOT NULL,
    status public.language_content_progress_status DEFAULT 'not_started'::public.language_content_progress_status NOT NULL
);


--
-- Name: language_path_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_path_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_path_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_path_items_id_seq OWNED BY public.language_path_items.id;


--
-- Name: language_placement_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_placement_attempts (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    status public.language_placement_attempt_status DEFAULT 'in_progress'::public.language_placement_attempt_status NOT NULL,
    is_retake boolean DEFAULT false NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    submitted_at timestamp with time zone
);


--
-- Name: language_placement_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_placement_attempts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_placement_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_placement_attempts_id_seq OWNED BY public.language_placement_attempts.id;


--
-- Name: language_placement_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_placement_questions (
    id integer NOT NULL,
    section_id integer NOT NULL,
    question_type character varying(32) NOT NULL,
    prompt_json jsonb NOT NULL,
    media_url character varying(1024),
    answer_key_json jsonb,
    max_points integer DEFAULT 1 NOT NULL,
    level_hint character varying(8),
    sort_order integer DEFAULT 0 NOT NULL
);


--
-- Name: language_placement_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_placement_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_placement_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_placement_questions_id_seq OWNED BY public.language_placement_questions.id;


--
-- Name: language_placement_responses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_placement_responses (
    id integer NOT NULL,
    attempt_id integer NOT NULL,
    question_id integer NOT NULL,
    response_json jsonb NOT NULL,
    score double precision,
    evaluation_metadata jsonb
);


--
-- Name: language_placement_responses_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_placement_responses_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_placement_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_placement_responses_id_seq OWNED BY public.language_placement_responses.id;


--
-- Name: language_placement_sections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_placement_sections (
    id integer NOT NULL,
    language_id integer NOT NULL,
    skill public.language_skill NOT NULL,
    title_ar character varying(200) NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL
);


--
-- Name: language_placement_sections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_placement_sections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_placement_sections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_placement_sections_id_seq OWNED BY public.language_placement_sections.id;


--
-- Name: language_products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_products (
    id integer NOT NULL,
    slug character varying(64) NOT NULL,
    name_ar character varying(200) NOT NULL,
    description_ar character varying(1000),
    price double precision DEFAULT 0 NOT NULL,
    currency character varying(10) DEFAULT 'SYP'::character varying NOT NULL,
    term_days integer DEFAULT 365 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_products_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_products_id_seq OWNED BY public.language_products.id;


--
-- Name: language_progress_snapshots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_progress_snapshots (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    snapshot_date date NOT NULL,
    overall_rank integer DEFAULT 0 NOT NULL,
    reading_rank integer DEFAULT 0 NOT NULL,
    listening_rank integer DEFAULT 0 NOT NULL,
    writing_rank integer DEFAULT 0 NOT NULL,
    speaking_rank integer DEFAULT 0 NOT NULL,
    xp_total integer DEFAULT 0 NOT NULL,
    vocabulary_count integer DEFAULT 0 NOT NULL,
    pronunciation_avg integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_progress_snapshots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_progress_snapshots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_progress_snapshots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_progress_snapshots_id_seq OWNED BY public.language_progress_snapshots.id;


--
-- Name: language_pronunciation_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_pronunciation_scores (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    overall integer DEFAULT 0 NOT NULL,
    clarity integer DEFAULT 0 NOT NULL,
    fluency integer DEFAULT 0 NOT NULL,
    pace integer DEFAULT 0 NOT NULL,
    stress integer DEFAULT 0 NOT NULL,
    intonation integer DEFAULT 0 NOT NULL,
    source character varying(20) DEFAULT 'conversation'::character varying NOT NULL,
    feedback text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_pronunciation_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_pronunciation_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_pronunciation_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_pronunciation_scores_id_seq OWNED BY public.language_pronunciation_scores.id;


--
-- Name: language_reading_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_reading_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    content_item_id integer NOT NULL,
    status public.language_content_progress_status DEFAULT 'not_started'::public.language_content_progress_status NOT NULL,
    score_percent double precision,
    completed_at timestamp with time zone,
    attempt_count integer DEFAULT 0 NOT NULL
);


--
-- Name: language_reading_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_reading_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_reading_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_reading_progress_id_seq OWNED BY public.language_reading_progress.id;


--
-- Name: language_scenario_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_scenario_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    scenario_key character varying(64) NOT NULL,
    scenario_id integer,
    status character varying(16) DEFAULT 'not_started'::character varying NOT NULL,
    completion_count integer DEFAULT 0 NOT NULL,
    best_score integer DEFAULT 0 NOT NULL,
    best_scores_json jsonb,
    last_played_at timestamp with time zone,
    first_completed_at timestamp with time zone
);


--
-- Name: language_scenario_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_scenario_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_scenario_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_scenario_progress_id_seq OWNED BY public.language_scenario_progress.id;


--
-- Name: language_skill_level_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_skill_level_state (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    skill public.language_skill NOT NULL,
    current_level public.language_level NOT NULL,
    consecutive_pass_count integer DEFAULT 0 NOT NULL,
    consecutive_fail_count integer DEFAULT 0 NOT NULL,
    last_level_change_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    recent_scores_json jsonb DEFAULT '[]'::jsonb NOT NULL
);


--
-- Name: language_skill_level_state_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_skill_level_state_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_skill_level_state_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_skill_level_state_id_seq OWNED BY public.language_skill_level_state.id;


--
-- Name: language_speaking_conversation_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_speaking_conversation_sessions (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    effective_level_at_start public.language_level,
    turn_count integer DEFAULT 0 NOT NULL,
    summary_json jsonb,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    scenario_id integer
);


--
-- Name: language_speaking_conversation_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_speaking_conversation_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_speaking_conversation_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_speaking_conversation_sessions_id_seq OWNED BY public.language_speaking_conversation_sessions.id;


--
-- Name: language_speaking_conversation_turns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_speaking_conversation_turns (
    id integer NOT NULL,
    session_id integer NOT NULL,
    student_id integer NOT NULL,
    turn_index integer NOT NULL,
    user_transcript text DEFAULT ''::text NOT NULL,
    assistant_reply text DEFAULT ''::text NOT NULL,
    user_media_object_id integer,
    reply_media_object_id integer,
    duration_seconds integer,
    evaluation_json jsonb,
    estimated_cefr public.language_level,
    scoring_version character varying(32) DEFAULT 'conversation_v1'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_speaking_conversation_turns_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_speaking_conversation_turns_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_speaking_conversation_turns_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_speaking_conversation_turns_id_seq OWNED BY public.language_speaking_conversation_turns.id;


--
-- Name: language_speaking_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_speaking_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    content_item_id integer NOT NULL,
    media_object_id integer NOT NULL,
    transcript text,
    metrics_json jsonb,
    level_estimate public.language_level,
    scoring_version character varying(32) DEFAULT 'rule_v1'::character varying NOT NULL,
    ai_evaluation_json jsonb,
    submitted_at timestamp with time zone DEFAULT now() NOT NULL,
    duration_seconds integer,
    completed_at timestamp with time zone
);


--
-- Name: language_speaking_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_speaking_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_speaking_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_speaking_progress_id_seq OWNED BY public.language_speaking_progress.id;


--
-- Name: language_streaks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_streaks (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    current_streak integer DEFAULT 0 NOT NULL,
    longest_streak integer DEFAULT 0 NOT NULL,
    last_activity_date date
);


--
-- Name: language_streaks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_streaks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_streaks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_streaks_id_seq OWNED BY public.language_streaks.id;


--
-- Name: language_student_achievements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_student_achievements (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    achievement_key character varying(64) NOT NULL,
    unlocked_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_student_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_student_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_student_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_student_achievements_id_seq OWNED BY public.language_student_achievements.id;


--
-- Name: language_student_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_student_profiles (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    onboarding_step public.language_onboarding_step DEFAULT 'select_language'::public.language_onboarding_step NOT NULL,
    selected_at timestamp with time zone,
    placement_completed_at timestamp with time zone,
    last_assessment_date timestamp with time zone,
    next_allowed_retake_date timestamp with time zone,
    target_level public.language_level,
    target_date date,
    certificate_level public.language_level,
    certificate_awarded_at timestamp with time zone,
    estimated_time_to_next_level character varying(64),
    target_progress_percent integer,
    preferences_json jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_student_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_student_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_student_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_student_profiles_id_seq OWNED BY public.language_student_profiles.id;


--
-- Name: language_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_subscriptions (
    id integer NOT NULL,
    student_id integer NOT NULL,
    product_id integer NOT NULL,
    payment_id integer,
    payment_status public.paymentstatus DEFAULT 'pending'::public.paymentstatus NOT NULL,
    activated_at timestamp with time zone,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_subscriptions_id_seq OWNED BY public.language_subscriptions.id;


--
-- Name: language_vocabulary_catalog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_vocabulary_catalog (
    id integer NOT NULL,
    word character varying(80) NOT NULL,
    part_of_speech character varying(40) DEFAULT ''::character varying NOT NULL,
    translation character varying(200) DEFAULT ''::character varying NOT NULL,
    definition text DEFAULT ''::text NOT NULL,
    context_theme character varying(60) DEFAULT ''::character varying NOT NULL,
    example_sentence text DEFAULT ''::text NOT NULL,
    cefr_level character varying(4) DEFAULT ''::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_vocabulary_catalog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_vocabulary_catalog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_vocabulary_catalog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_vocabulary_catalog_id_seq OWNED BY public.language_vocabulary_catalog.id;


--
-- Name: language_vocabulary_catalog_seen; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_vocabulary_catalog_seen (
    id integer NOT NULL,
    student_id integer NOT NULL,
    catalog_id integer NOT NULL,
    seen_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: language_vocabulary_catalog_seen_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_vocabulary_catalog_seen_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_vocabulary_catalog_seen_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_vocabulary_catalog_seen_id_seq OWNED BY public.language_vocabulary_catalog_seen.id;


--
-- Name: language_vocabulary_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_vocabulary_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    language_id integer NOT NULL,
    lemma character varying(120) NOT NULL,
    first_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    mastery_score double precision DEFAULT 0 NOT NULL,
    status public.language_vocabulary_status DEFAULT 'new'::public.language_vocabulary_status NOT NULL,
    review_count integer DEFAULT 0 NOT NULL,
    last_reviewed_at timestamp with time zone,
    next_review_at timestamp with time zone,
    interval_days integer DEFAULT 1 NOT NULL,
    ease_factor double precision DEFAULT '2.5'::double precision NOT NULL,
    repetition_number integer DEFAULT 0 NOT NULL
);


--
-- Name: language_vocabulary_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_vocabulary_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_vocabulary_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_vocabulary_progress_id_seq OWNED BY public.language_vocabulary_progress.id;


--
-- Name: language_writing_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.language_writing_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    content_item_id integer NOT NULL,
    submitted_text text NOT NULL,
    word_count integer DEFAULT 0 NOT NULL,
    metrics_json jsonb,
    level_estimate public.language_level,
    scoring_version character varying(32) DEFAULT 'rule_v1'::character varying NOT NULL,
    ai_evaluation_json jsonb,
    submitted_at timestamp with time zone DEFAULT now() NOT NULL,
    score_percent double precision,
    completed_at timestamp with time zone
);


--
-- Name: language_writing_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.language_writing_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: language_writing_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.language_writing_progress_id_seq OWNED BY public.language_writing_progress.id;


--
-- Name: languages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.languages (
    id integer NOT NULL,
    code character varying(16) NOT NULL,
    name_en character varying(120) NOT NULL,
    name_ar character varying(120) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: languages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.languages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: languages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.languages_id_seq OWNED BY public.languages.id;


--
-- Name: lesson_assets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lesson_assets (
    id integer NOT NULL,
    lesson_id integer NOT NULL,
    asset_type public.lessonassettype NOT NULL,
    storage_path character varying(1024) NOT NULL,
    original_filename character varying(500),
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    media_object_id integer,
    mime_type character varying(128),
    file_size_bytes bigint
);


--
-- Name: lesson_assets_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lesson_assets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lesson_assets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lesson_assets_id_seq OWNED BY public.lesson_assets.id;


--
-- Name: lessons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lessons (
    id integer NOT NULL,
    teacher_id integer NOT NULL,
    title character varying(500) NOT NULL,
    subject character varying(120) NOT NULL,
    grade character varying(50) NOT NULL,
    status public.lessonstatus NOT NULL,
    pdf_path character varying(1024),
    voice_path character varying(1024),
    persona_prompt text,
    preview text,
    page_count integer,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    description text,
    video_url character varying(1024),
    sort_order integer DEFAULT 0,
    is_visible boolean DEFAULT true,
    course_id integer,
    homework_path character varying(1024),
    content_type character varying(32) DEFAULT 'video'::character varying,
    insights_json jsonb
);


--
-- Name: lessons_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lessons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lessons_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lessons_id_seq OWNED BY public.lessons.id;


--
-- Name: media_objects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media_objects (
    id integer NOT NULL,
    storage_provider character varying(32) DEFAULT 'local'::character varying NOT NULL,
    storage_key character varying(1024) NOT NULL,
    public_url character varying(2048),
    mime_type character varying(128),
    file_size_bytes bigint,
    original_filename character varying(500),
    uploaded_by_user_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: media_objects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.media_objects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: media_objects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.media_objects_id_seq OWNED BY public.media_objects.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer NOT NULL,
    channel public.notificationchannel DEFAULT 'in_app'::public.notificationchannel NOT NULL,
    type character varying(64) DEFAULT 'system'::character varying NOT NULL,
    title character varying(200) NOT NULL,
    body text NOT NULL,
    data_json text,
    payload jsonb,
    is_read boolean DEFAULT false NOT NULL,
    read_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- Name: parent_notification_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parent_notification_settings (
    id integer NOT NULL,
    parent_id integer NOT NULL,
    student_id integer NOT NULL,
    login_alerts boolean DEFAULT true NOT NULL,
    logout_alerts boolean DEFAULT true NOT NULL,
    lesson_alerts boolean DEFAULT true NOT NULL,
    quiz_alerts boolean DEFAULT true NOT NULL,
    low_score_alerts boolean DEFAULT true NOT NULL,
    inactivity_alerts boolean DEFAULT true NOT NULL,
    planner_alerts boolean DEFAULT true NOT NULL,
    inactivity_days integer DEFAULT 3 NOT NULL,
    low_score_threshold integer DEFAULT 60 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: parent_notification_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parent_notification_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parent_notification_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parent_notification_settings_id_seq OWNED BY public.parent_notification_settings.id;


--
-- Name: parent_student_links; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parent_student_links (
    id integer NOT NULL,
    parent_id integer NOT NULL,
    student_id integer NOT NULL,
    relationship_label character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_viewed_at timestamp with time zone
);


--
-- Name: parent_student_links_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parent_student_links_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parent_student_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parent_student_links_id_seq OWNED BY public.parent_student_links.id;


--
-- Name: payment_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_items (
    id integer NOT NULL,
    payment_id integer NOT NULL,
    course_id integer,
    unit_price double precision NOT NULL,
    product_type public.payment_item_product_type DEFAULT 'course'::public.payment_item_product_type NOT NULL,
    language_product_id integer,
    CONSTRAINT ck_payment_items_product_target CHECK ((((product_type = 'course'::public.payment_item_product_type) AND (course_id IS NOT NULL) AND (language_product_id IS NULL)) OR ((product_type = 'language'::public.payment_item_product_type) AND (language_product_id IS NOT NULL) AND (course_id IS NULL))))
);


--
-- Name: payment_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payment_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payment_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payment_items_id_seq OWNED BY public.payment_items.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    student_id integer NOT NULL,
    total_amount double precision NOT NULL,
    currency character varying(10) NOT NULL,
    method public.paymentmethod,
    status public.paymentstatus NOT NULL,
    reference character varying(64),
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: planner_chat_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.planner_chat_messages (
    id integer NOT NULL,
    student_id integer NOT NULL,
    role character varying(16) NOT NULL,
    content text NOT NULL,
    metadata_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: planner_chat_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.planner_chat_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: planner_chat_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.planner_chat_messages_id_seq OWNED BY public.planner_chat_messages.id;


--
-- Name: planner_life_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.planner_life_events (
    id integer NOT NULL,
    student_id integer NOT NULL,
    title character varying(255) NOT NULL,
    event_type public.lifeeventtype NOT NULL,
    day_of_week integer,
    event_date timestamp with time zone,
    start_time character varying(8),
    duration_minutes integer NOT NULL,
    is_blocking boolean NOT NULL,
    subject character varying(120),
    metadata_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: planner_life_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.planner_life_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: planner_life_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.planner_life_events_id_seq OWNED BY public.planner_life_events.id;


--
-- Name: planner_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.planner_profiles (
    id integer NOT NULL,
    student_id integer NOT NULL,
    preferred_period character varying(32) NOT NULL,
    school_start character varying(8) NOT NULL,
    school_end character varying(8) NOT NULL,
    max_daily_minutes integer NOT NULL,
    weak_subjects_json text NOT NULL,
    memory_json text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: planner_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.planner_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: planner_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.planner_profiles_id_seq OWNED BY public.planner_profiles.id;


--
-- Name: planner_schedule_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.planner_schedule_slots (
    id integer NOT NULL,
    student_id integer NOT NULL,
    subject character varying(120) NOT NULL,
    scheduled_at timestamp with time zone NOT NULL,
    duration_minutes integer NOT NULL,
    priority integer NOT NULL,
    status public.scheduleslotstatus NOT NULL,
    reasoning text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: planner_schedule_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.planner_schedule_slots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: planner_schedule_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.planner_schedule_slots_id_seq OWNED BY public.planner_schedule_slots.id;


--
-- Name: quiz_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quiz_attempts (
    id integer NOT NULL,
    lesson_id integer NOT NULL,
    student_id integer NOT NULL,
    answers_json text NOT NULL,
    correct_count integer NOT NULL,
    feedback_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.quiz_attempts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: quiz_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.quiz_attempts_id_seq OWNED BY public.quiz_attempts.id;


--
-- Name: quiz_questions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.quiz_questions (
    id integer NOT NULL,
    lesson_id integer NOT NULL,
    question text NOT NULL,
    options_json text NOT NULL,
    correct_index integer NOT NULL,
    hint text,
    sort_order integer NOT NULL
);


--
-- Name: quiz_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.quiz_questions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: quiz_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.quiz_questions_id_seq OWNED BY public.quiz_questions.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    slug character varying(32) NOT NULL,
    name_ar character varying(120) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: routine_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.routine_slots (
    id integer NOT NULL,
    profile_id integer NOT NULL,
    day_of_week integer NOT NULL,
    start_time character varying(8) NOT NULL,
    end_time character varying(8) NOT NULL,
    activity_type character varying(32) NOT NULL,
    title character varying(255) NOT NULL,
    subject character varying(120),
    is_fixed boolean DEFAULT false NOT NULL,
    status character varying(16) DEFAULT 'planned'::character varying NOT NULL
);


--
-- Name: routine_slots_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.routine_slots_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: routine_slots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.routine_slots_id_seq OWNED BY public.routine_slots.id;


--
-- Name: schedule_optimization_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_optimization_logs (
    id integer NOT NULL,
    student_id integer NOT NULL,
    schedule_id integer,
    event_type character varying(64) NOT NULL,
    payload_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: schedule_optimization_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.schedule_optimization_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: schedule_optimization_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.schedule_optimization_logs_id_seq OWNED BY public.schedule_optimization_logs.id;


--
-- Name: student_achievements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_achievements (
    id integer NOT NULL,
    student_id integer NOT NULL,
    achievement_key character varying(80) NOT NULL,
    icon character varying(16) DEFAULT ''::character varying NOT NULL,
    title character varying(200) NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    unlocked_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: student_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_achievements_id_seq OWNED BY public.student_achievements.id;


--
-- Name: student_activity_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_activity_events (
    id integer NOT NULL,
    student_id integer NOT NULL,
    event_type public.activityeventtype NOT NULL,
    title character varying(500) NOT NULL,
    description text,
    payload_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_activity_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_activity_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_activity_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_activity_events_id_seq OWNED BY public.student_activity_events.id;


--
-- Name: student_activity_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_activity_sessions (
    id integer NOT NULL,
    student_id integer NOT NULL,
    auth_session_id integer,
    login_at timestamp with time zone NOT NULL,
    logout_at timestamp with time zone,
    logout_reason public.activitysessionlogoutreason,
    active_minutes integer DEFAULT 0 NOT NULL,
    last_active_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_activity_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_activity_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_activity_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_activity_sessions_id_seq OWNED BY public.student_activity_sessions.id;


--
-- Name: student_analytics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_analytics (
    student_id integer NOT NULL,
    completion_rate double precision DEFAULT '0'::double precision NOT NULL,
    average_score double precision,
    total_study_hours double precision DEFAULT '0'::double precision NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_attendance_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_attendance_records (
    id integer NOT NULL,
    student_id integer NOT NULL,
    date date NOT NULL,
    status public.attendancestatus NOT NULL,
    study_minutes integer NOT NULL,
    consistency_score integer NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_attendance_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_attendance_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_attendance_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_attendance_records_id_seq OWNED BY public.student_attendance_records.id;


--
-- Name: student_course_access; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_course_access (
    id integer NOT NULL,
    student_id integer NOT NULL,
    course_id integer NOT NULL,
    payment_status public.paymentstatus NOT NULL,
    unlocked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    activated_at timestamp with time zone,
    expires_at timestamp with time zone
);


--
-- Name: student_course_access_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_course_access_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_course_access_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_course_access_id_seq OWNED BY public.student_course_access.id;


--
-- Name: student_engagement_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_engagement_events (
    id integer NOT NULL,
    student_id integer NOT NULL,
    activity_session_id integer,
    event_type public.engagementeventtype NOT NULL,
    resource_type character varying(64),
    resource_id integer,
    path character varying(512),
    metadata_json text,
    counted_seconds integer DEFAULT 0 NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_engagement_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_engagement_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_engagement_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_engagement_events_id_seq OWNED BY public.student_engagement_events.id;


--
-- Name: student_grade_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_grade_reports (
    id integer NOT NULL,
    student_id integer NOT NULL,
    course_id integer NOT NULL,
    average_score double precision,
    attendance_percentage double precision,
    completion_percentage double precision,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_grade_reports_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_grade_reports_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_grade_reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_grade_reports_id_seq OWNED BY public.student_grade_reports.id;


--
-- Name: student_learning_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_learning_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    weak_topics_json text DEFAULT '[]'::text NOT NULL,
    strong_topics_json text DEFAULT '[]'::text NOT NULL,
    repeated_mistakes_json text DEFAULT '[]'::text NOT NULL,
    lesson_history_json text DEFAULT '[]'::text NOT NULL,
    memory_summary text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_learning_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_learning_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_learning_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_learning_profiles_id_seq OWNED BY public.student_learning_profiles.id;


--
-- Name: student_lesson_progress; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_lesson_progress (
    id integer NOT NULL,
    student_id integer NOT NULL,
    lesson_id integer NOT NULL,
    completed_at timestamp with time zone,
    video_progress_percent double precision DEFAULT '0'::double precision NOT NULL,
    pdf_progress_percent double precision DEFAULT '0'::double precision NOT NULL,
    pdf_opened boolean DEFAULT false NOT NULL,
    quiz_submitted boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    quiz_score_percent double precision DEFAULT '0'::double precision NOT NULL,
    completion_type character varying(32),
    completion_percentage double precision DEFAULT '0'::double precision NOT NULL,
    started_at timestamp with time zone,
    video_last_watched_at timestamp with time zone
);


--
-- Name: student_lesson_progress_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_lesson_progress_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_lesson_progress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_lesson_progress_id_seq OWNED BY public.student_lesson_progress.id;


--
-- Name: student_parent_note_reads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_parent_note_reads (
    id integer NOT NULL,
    note_id integer NOT NULL,
    parent_id integer NOT NULL,
    read_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_parent_note_reads_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_parent_note_reads_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_parent_note_reads_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_parent_note_reads_id_seq OWNED BY public.student_parent_note_reads.id;


--
-- Name: student_parent_note_replies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_parent_note_replies (
    id integer NOT NULL,
    note_id integer NOT NULL,
    author_id integer NOT NULL,
    author_role character varying(16) NOT NULL,
    body text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_parent_note_replies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_parent_note_replies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_parent_note_replies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_parent_note_replies_id_seq OWNED BY public.student_parent_note_replies.id;


--
-- Name: student_parent_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_parent_notes (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    student_id integer NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    category character varying(32) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    status character varying(16) DEFAULT 'new'::character varying NOT NULL,
    priority character varying(16) DEFAULT 'medium'::character varying NOT NULL,
    closed_at timestamp with time zone,
    closed_by_user_id integer
);


--
-- Name: student_parent_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_parent_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_parent_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_parent_notes_id_seq OWNED BY public.student_parent_notes.id;


--
-- Name: student_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    interests_json text NOT NULL,
    difficulty character varying(50) NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    grade integer,
    onboarding_step character varying(32) DEFAULT 'grade'::character varying,
    onboarding_completed_at timestamp with time zone,
    payment_completed_at timestamp with time zone,
    parent_link_code character varying(16),
    last_activity_at timestamp with time zone,
    age integer,
    learning_style character varying(32) DEFAULT 'theoretical'::character varying NOT NULL,
    future_goal character varying(32) DEFAULT 'undecided'::character varying NOT NULL,
    preferred_explanation_style character varying(32) DEFAULT 'normal'::character varying NOT NULL,
    personality_mode character varying(32) DEFAULT 'friendly_teacher'::character varying NOT NULL,
    hobbies_json text DEFAULT '[]'::text NOT NULL
);


--
-- Name: student_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_profiles_id_seq OWNED BY public.student_profiles.id;


--
-- Name: student_routine_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_routine_profiles (
    id integer NOT NULL,
    student_id integer NOT NULL,
    grade_level character varying(20) DEFAULT ''::character varying NOT NULL,
    school_start character varying(8) DEFAULT '07:30'::character varying NOT NULL,
    school_end character varying(8) DEFAULT '13:00'::character varying NOT NULL,
    wake_time character varying(8) DEFAULT '06:30'::character varying NOT NULL,
    sleep_time character varying(8) DEFAULT '22:00'::character varying NOT NULL,
    school_days_json text DEFAULT '[1,2,3,4,0]'::text NOT NULL,
    activities_json text DEFAULT '{}'::text NOT NULL,
    onboarding_complete boolean DEFAULT false NOT NULL,
    chat_history_json text DEFAULT '[]'::text NOT NULL,
    chat_stage character varying(32) DEFAULT 'start'::character varying NOT NULL,
    day_data_json text DEFAULT '{}'::text NOT NULL,
    updated_at text DEFAULT now() NOT NULL
);


--
-- Name: student_routine_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_routine_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_routine_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_routine_profiles_id_seq OWNED BY public.student_routine_profiles.id;


--
-- Name: student_schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_schedules (
    id integer NOT NULL,
    student_id integer NOT NULL,
    week_start date NOT NULL,
    status character varying(20) NOT NULL,
    generated_by character varying(32) NOT NULL,
    meta_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: student_schedules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_schedules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_schedules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_schedules_id_seq OWNED BY public.student_schedules.id;


--
-- Name: student_study_streaks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_study_streaks (
    id integer NOT NULL,
    student_id integer NOT NULL,
    current_streak_days integer DEFAULT 0 NOT NULL,
    longest_streak_days integer DEFAULT 0 NOT NULL,
    task_streak_days integer DEFAULT 0 NOT NULL,
    last_study_date date,
    last_task_date date,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: student_study_streaks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_study_streaks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_study_streaks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_study_streaks_id_seq OWNED BY public.student_study_streaks.id;


--
-- Name: student_subject_choices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_subject_choices (
    id integer NOT NULL,
    student_id integer NOT NULL,
    subject_id integer NOT NULL
);


--
-- Name: student_subject_choices_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_subject_choices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_subject_choices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_subject_choices_id_seq OWNED BY public.student_subject_choices.id;


--
-- Name: student_teacher_choices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_teacher_choices (
    id integer NOT NULL,
    student_id integer NOT NULL,
    subject_id integer NOT NULL,
    teacher_profile_id integer NOT NULL
);


--
-- Name: student_teacher_choices_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_teacher_choices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_teacher_choices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_teacher_choices_id_seq OWNED BY public.student_teacher_choices.id;


--
-- Name: student_xp; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.student_xp (
    id integer NOT NULL,
    student_id integer NOT NULL,
    total_xp integer DEFAULT 0 NOT NULL,
    level integer DEFAULT 1 NOT NULL,
    awarded_keys_json text DEFAULT '[]'::text NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: student_xp_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.student_xp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: student_xp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.student_xp_id_seq OWNED BY public.student_xp.id;


--
-- Name: study_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.study_sessions (
    id integer NOT NULL,
    schedule_id integer NOT NULL,
    student_id integer NOT NULL,
    subject character varying(120) NOT NULL,
    title character varying(255) NOT NULL,
    difficulty character varying(20) NOT NULL,
    session_type character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    starts_at timestamp with time zone NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    lesson_id integer,
    sort_order integer NOT NULL,
    notes text
);


--
-- Name: study_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.study_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: study_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.study_sessions_id_seq OWNED BY public.study_sessions.id;


--
-- Name: subjects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subjects (
    id integer NOT NULL,
    name_ar character varying(120) NOT NULL,
    slug character varying(80) NOT NULL,
    grade integer NOT NULL,
    is_active boolean NOT NULL
);


--
-- Name: subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.subjects_id_seq OWNED BY public.subjects.id;


--
-- Name: teacher_achievements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_achievements (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    title character varying(255) NOT NULL,
    year integer,
    description text,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_pinned boolean DEFAULT false NOT NULL
);


--
-- Name: teacher_achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_achievements_id_seq OWNED BY public.teacher_achievements.id;


--
-- Name: teacher_analytics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_analytics (
    teacher_profile_id integer NOT NULL,
    total_students integer DEFAULT 0 NOT NULL,
    total_courses integer DEFAULT 0 NOT NULL,
    average_completion double precision DEFAULT '0'::double precision NOT NULL,
    average_rating double precision,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: teacher_professional_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_professional_documents (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    title character varying(255) NOT NULL,
    document_type character varying(32) DEFAULT 'certificate'::character varying NOT NULL,
    file_url character varying(1024) NOT NULL,
    original_filename character varying(512),
    mime_type character varying(128),
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: teacher_professional_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_professional_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_professional_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_professional_documents_id_seq OWNED BY public.teacher_professional_documents.id;


--
-- Name: teacher_profile_grades; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_profile_grades (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    grade integer NOT NULL
);


--
-- Name: teacher_profile_grades_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_profile_grades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_profile_grades_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_profile_grades_id_seq OWNED BY public.teacher_profile_grades.id;


--
-- Name: teacher_profile_subjects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_profile_subjects (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    subject_id integer NOT NULL
);


--
-- Name: teacher_profile_subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_profile_subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_profile_subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_profile_subjects_id_seq OWNED BY public.teacher_profile_subjects.id;


--
-- Name: teacher_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_profiles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    full_name character varying(255) NOT NULL,
    image_url character varying(1024),
    bio text,
    rating double precision NOT NULL,
    student_count integer NOT NULL,
    active boolean NOT NULL,
    setup_completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    impact_total_students integer,
    impact_grade12_students integer,
    impact_completed_subject integer,
    impact_excellent_grades integer,
    impact_years_teaching integer,
    philosophy_teaching_style text,
    philosophy_lesson_approach text,
    philosophy_exam_preparation text,
    teacher_teaching_style character varying(32) DEFAULT 'step_by_step'::character varying NOT NULL,
    teacher_tone character varying(32) DEFAULT 'balanced'::character varying NOT NULL,
    teacher_question_style character varying(32) DEFAULT 'mixed'::character varying NOT NULL,
    teacher_motivation_level character varying(32) DEFAULT 'medium'::character varying NOT NULL,
    teacher_display_name character varying(255),
    teacher_signature_phrase character varying(500)
);


--
-- Name: teacher_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_profiles_id_seq OWNED BY public.teacher_profiles.id;


--
-- Name: teacher_qualifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_qualifications (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    title character varying(255) NOT NULL,
    institution character varying(255),
    year integer,
    description text,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: teacher_qualifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_qualifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_qualifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_qualifications_id_seq OWNED BY public.teacher_qualifications.id;


--
-- Name: teacher_student_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_student_notes (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    student_id integer NOT NULL,
    note_text text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: teacher_student_notes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_student_notes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_student_notes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_student_notes_id_seq OWNED BY public.teacher_student_notes.id;


--
-- Name: teacher_teaching_experiences; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_teaching_experiences (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    title character varying(255) NOT NULL,
    organization character varying(255),
    year_from integer,
    year_to integer,
    description text,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: teacher_teaching_experiences_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_teaching_experiences_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_teaching_experiences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_teaching_experiences_id_seq OWNED BY public.teacher_teaching_experiences.id;


--
-- Name: teacher_voice_samples; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_voice_samples (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    storage_path character varying(1024) NOT NULL,
    duration_seconds double precision DEFAULT 0 NOT NULL,
    uploaded_at timestamp with time zone DEFAULT now(),
    processing_status character varying(32) DEFAULT 'pending'::character varying NOT NULL,
    error_message text,
    transcript text,
    persona_prompt text,
    quality_score double precision,
    quality_tier character varying(32),
    clone_confidence double precision,
    transcript_quality double precision,
    noise_score double precision,
    speech_score double precision,
    preview_audio_path character varying(1024),
    teacher_accepted boolean DEFAULT false NOT NULL,
    quality_details_json text,
    elevenlabs_voice_id character varying(128),
    elevenlabs_requires_verification boolean DEFAULT false NOT NULL
);


--
-- Name: teacher_voice_samples_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_voice_samples_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_voice_samples_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_voice_samples_id_seq OWNED BY public.teacher_voice_samples.id;


--
-- Name: teacher_why_study_points; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teacher_why_study_points (
    id integer NOT NULL,
    teacher_profile_id integer NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    sort_order integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: teacher_why_study_points_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teacher_why_study_points_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teacher_why_study_points_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.teacher_why_study_points_id_seq OWNED BY public.teacher_why_study_points.id;


--
-- Name: two_factor_challenges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.two_factor_challenges (
    id integer NOT NULL,
    user_id integer NOT NULL,
    purpose character varying(16) NOT NULL,
    challenge_token_hash character varying(64) NOT NULL,
    code_hash character varying(64) NOT NULL,
    failed_attempts integer DEFAULT 0 NOT NULL,
    resend_count integer DEFAULT 0 NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    last_sent_at timestamp with time zone NOT NULL,
    ip_address character varying(64),
    device_name character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: two_factor_challenges_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.two_factor_challenges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: two_factor_challenges_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.two_factor_challenges_id_seq OWNED BY public.two_factor_challenges.id;


--
-- Name: user_roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_roles (
    id integer NOT NULL,
    user_id integer NOT NULL,
    role_id integer NOT NULL,
    granted_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: user_roles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_roles_id_seq OWNED BY public.user_roles.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    role character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    email_verified_at timestamp with time zone,
    two_factor_enabled boolean DEFAULT false NOT NULL,
    two_factor_method character varying(16)
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: ai_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_jobs ALTER COLUMN id SET DEFAULT nextval('public.ai_jobs_id_seq'::regclass);


--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- Name: auth_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_sessions ALTER COLUMN id SET DEFAULT nextval('public.auth_sessions_id_seq'::regclass);


--
-- Name: availability_blocks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availability_blocks ALTER COLUMN id SET DEFAULT nextval('public.availability_blocks_id_seq'::regclass);


--
-- Name: chat_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages ALTER COLUMN id SET DEFAULT nextval('public.chat_messages_id_seq'::regclass);


--
-- Name: content_chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_chunks ALTER COLUMN id SET DEFAULT nextval('public.content_chunks_id_seq'::regclass);


--
-- Name: conversation_message_reads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message_reads ALTER COLUMN id SET DEFAULT nextval('public.conversation_message_reads_id_seq'::regclass);


--
-- Name: conversation_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_messages ALTER COLUMN id SET DEFAULT nextval('public.conversation_messages_id_seq'::regclass);


--
-- Name: conversation_participants id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_participants ALTER COLUMN id SET DEFAULT nextval('public.conversation_participants_id_seq'::regclass);


--
-- Name: conversation_threads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_threads ALTER COLUMN id SET DEFAULT nextval('public.conversation_threads_id_seq'::regclass);


--
-- Name: course_quiz_answers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_answers ALTER COLUMN id SET DEFAULT nextval('public.course_quiz_answers_id_seq'::regclass);


--
-- Name: course_quiz_attempts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_attempts ALTER COLUMN id SET DEFAULT nextval('public.course_quiz_attempts_id_seq'::regclass);


--
-- Name: course_quiz_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_questions ALTER COLUMN id SET DEFAULT nextval('public.course_quiz_questions_id_seq'::regclass);


--
-- Name: course_quizzes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quizzes ALTER COLUMN id SET DEFAULT nextval('public.course_quizzes_id_seq'::regclass);


--
-- Name: courses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses ALTER COLUMN id SET DEFAULT nextval('public.courses_id_seq'::regclass);


--
-- Name: email_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_tokens ALTER COLUMN id SET DEFAULT nextval('public.email_tokens_id_seq'::regclass);


--
-- Name: exams id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams ALTER COLUMN id SET DEFAULT nextval('public.exams_id_seq'::regclass);


--
-- Name: language_activity_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_activity_log ALTER COLUMN id SET DEFAULT nextval('public.language_activity_log_id_seq'::regclass);


--
-- Name: language_ai_usage id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_ai_usage ALTER COLUMN id SET DEFAULT nextval('public.language_ai_usage_id_seq'::regclass);


--
-- Name: language_assessment_skill_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessment_skill_scores ALTER COLUMN id SET DEFAULT nextval('public.language_assessment_skill_scores_id_seq'::regclass);


--
-- Name: language_assessments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessments ALTER COLUMN id SET DEFAULT nextval('public.language_assessments_id_seq'::regclass);


--
-- Name: language_certificates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_certificates ALTER COLUMN id SET DEFAULT nextval('public.language_certificates_id_seq'::regclass);


--
-- Name: language_component_mastery id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_component_mastery ALTER COLUMN id SET DEFAULT nextval('public.language_component_mastery_id_seq'::regclass);


--
-- Name: language_content_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_content_items ALTER COLUMN id SET DEFAULT nextval('public.language_content_items_id_seq'::regclass);


--
-- Name: language_conversation_scenarios id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_conversation_scenarios ALTER COLUMN id SET DEFAULT nextval('public.language_conversation_scenarios_id_seq'::regclass);


--
-- Name: language_curriculum_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_curriculum_progress ALTER COLUMN id SET DEFAULT nextval('public.language_curriculum_progress_id_seq'::regclass);


--
-- Name: language_error_patterns id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_error_patterns ALTER COLUMN id SET DEFAULT nextval('public.language_error_patterns_id_seq'::regclass);


--
-- Name: language_generated_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_generated_questions ALTER COLUMN id SET DEFAULT nextval('public.language_generated_questions_id_seq'::regclass);


--
-- Name: language_knowledge_components id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_knowledge_components ALTER COLUMN id SET DEFAULT nextval('public.language_knowledge_components_id_seq'::regclass);


--
-- Name: language_learning_paths id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_learning_paths ALTER COLUMN id SET DEFAULT nextval('public.language_learning_paths_id_seq'::regclass);


--
-- Name: language_lesson_audio_cache id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_lesson_audio_cache ALTER COLUMN id SET DEFAULT nextval('public.language_lesson_audio_cache_id_seq'::regclass);


--
-- Name: language_listening_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_listening_progress ALTER COLUMN id SET DEFAULT nextval('public.language_listening_progress_id_seq'::regclass);


--
-- Name: language_path_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_path_items ALTER COLUMN id SET DEFAULT nextval('public.language_path_items_id_seq'::regclass);


--
-- Name: language_placement_attempts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_attempts ALTER COLUMN id SET DEFAULT nextval('public.language_placement_attempts_id_seq'::regclass);


--
-- Name: language_placement_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_questions ALTER COLUMN id SET DEFAULT nextval('public.language_placement_questions_id_seq'::regclass);


--
-- Name: language_placement_responses id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_responses ALTER COLUMN id SET DEFAULT nextval('public.language_placement_responses_id_seq'::regclass);


--
-- Name: language_placement_sections id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_sections ALTER COLUMN id SET DEFAULT nextval('public.language_placement_sections_id_seq'::regclass);


--
-- Name: language_products id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_products ALTER COLUMN id SET DEFAULT nextval('public.language_products_id_seq'::regclass);


--
-- Name: language_progress_snapshots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_progress_snapshots ALTER COLUMN id SET DEFAULT nextval('public.language_progress_snapshots_id_seq'::regclass);


--
-- Name: language_pronunciation_scores id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_pronunciation_scores ALTER COLUMN id SET DEFAULT nextval('public.language_pronunciation_scores_id_seq'::regclass);


--
-- Name: language_reading_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_reading_progress ALTER COLUMN id SET DEFAULT nextval('public.language_reading_progress_id_seq'::regclass);


--
-- Name: language_scenario_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_scenario_progress ALTER COLUMN id SET DEFAULT nextval('public.language_scenario_progress_id_seq'::regclass);


--
-- Name: language_skill_level_state id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_skill_level_state ALTER COLUMN id SET DEFAULT nextval('public.language_skill_level_state_id_seq'::regclass);


--
-- Name: language_speaking_conversation_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_sessions ALTER COLUMN id SET DEFAULT nextval('public.language_speaking_conversation_sessions_id_seq'::regclass);


--
-- Name: language_speaking_conversation_turns id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_turns ALTER COLUMN id SET DEFAULT nextval('public.language_speaking_conversation_turns_id_seq'::regclass);


--
-- Name: language_speaking_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_progress ALTER COLUMN id SET DEFAULT nextval('public.language_speaking_progress_id_seq'::regclass);


--
-- Name: language_streaks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_streaks ALTER COLUMN id SET DEFAULT nextval('public.language_streaks_id_seq'::regclass);


--
-- Name: language_student_achievements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_achievements ALTER COLUMN id SET DEFAULT nextval('public.language_student_achievements_id_seq'::regclass);


--
-- Name: language_student_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_profiles ALTER COLUMN id SET DEFAULT nextval('public.language_student_profiles_id_seq'::regclass);


--
-- Name: language_subscriptions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_subscriptions ALTER COLUMN id SET DEFAULT nextval('public.language_subscriptions_id_seq'::regclass);


--
-- Name: language_vocabulary_catalog id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog ALTER COLUMN id SET DEFAULT nextval('public.language_vocabulary_catalog_id_seq'::regclass);


--
-- Name: language_vocabulary_catalog_seen id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog_seen ALTER COLUMN id SET DEFAULT nextval('public.language_vocabulary_catalog_seen_id_seq'::regclass);


--
-- Name: language_vocabulary_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_progress ALTER COLUMN id SET DEFAULT nextval('public.language_vocabulary_progress_id_seq'::regclass);


--
-- Name: language_writing_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_writing_progress ALTER COLUMN id SET DEFAULT nextval('public.language_writing_progress_id_seq'::regclass);


--
-- Name: languages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages ALTER COLUMN id SET DEFAULT nextval('public.languages_id_seq'::regclass);


--
-- Name: lesson_assets id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_assets ALTER COLUMN id SET DEFAULT nextval('public.lesson_assets_id_seq'::regclass);


--
-- Name: lessons id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lessons ALTER COLUMN id SET DEFAULT nextval('public.lessons_id_seq'::regclass);


--
-- Name: media_objects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_objects ALTER COLUMN id SET DEFAULT nextval('public.media_objects_id_seq'::regclass);


--
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- Name: parent_notification_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notification_settings ALTER COLUMN id SET DEFAULT nextval('public.parent_notification_settings_id_seq'::regclass);


--
-- Name: parent_student_links id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student_links ALTER COLUMN id SET DEFAULT nextval('public.parent_student_links_id_seq'::regclass);


--
-- Name: payment_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_items ALTER COLUMN id SET DEFAULT nextval('public.payment_items_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: planner_chat_messages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_chat_messages ALTER COLUMN id SET DEFAULT nextval('public.planner_chat_messages_id_seq'::regclass);


--
-- Name: planner_life_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_life_events ALTER COLUMN id SET DEFAULT nextval('public.planner_life_events_id_seq'::regclass);


--
-- Name: planner_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_profiles ALTER COLUMN id SET DEFAULT nextval('public.planner_profiles_id_seq'::regclass);


--
-- Name: planner_schedule_slots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_schedule_slots ALTER COLUMN id SET DEFAULT nextval('public.planner_schedule_slots_id_seq'::regclass);


--
-- Name: quiz_attempts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quiz_attempts ALTER COLUMN id SET DEFAULT nextval('public.quiz_attempts_id_seq'::regclass);


--
-- Name: quiz_questions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quiz_questions ALTER COLUMN id SET DEFAULT nextval('public.quiz_questions_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: routine_slots id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.routine_slots ALTER COLUMN id SET DEFAULT nextval('public.routine_slots_id_seq'::regclass);


--
-- Name: schedule_optimization_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_optimization_logs ALTER COLUMN id SET DEFAULT nextval('public.schedule_optimization_logs_id_seq'::regclass);


--
-- Name: student_achievements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_achievements ALTER COLUMN id SET DEFAULT nextval('public.student_achievements_id_seq'::regclass);


--
-- Name: student_activity_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_activity_events ALTER COLUMN id SET DEFAULT nextval('public.student_activity_events_id_seq'::regclass);


--
-- Name: student_activity_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_activity_sessions ALTER COLUMN id SET DEFAULT nextval('public.student_activity_sessions_id_seq'::regclass);


--
-- Name: student_attendance_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_attendance_records ALTER COLUMN id SET DEFAULT nextval('public.student_attendance_records_id_seq'::regclass);


--
-- Name: student_course_access id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_course_access ALTER COLUMN id SET DEFAULT nextval('public.student_course_access_id_seq'::regclass);


--
-- Name: student_engagement_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_engagement_events ALTER COLUMN id SET DEFAULT nextval('public.student_engagement_events_id_seq'::regclass);


--
-- Name: student_grade_reports id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_grade_reports ALTER COLUMN id SET DEFAULT nextval('public.student_grade_reports_id_seq'::regclass);


--
-- Name: student_learning_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_learning_profiles ALTER COLUMN id SET DEFAULT nextval('public.student_learning_profiles_id_seq'::regclass);


--
-- Name: student_lesson_progress id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_lesson_progress ALTER COLUMN id SET DEFAULT nextval('public.student_lesson_progress_id_seq'::regclass);


--
-- Name: student_parent_note_reads id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_reads ALTER COLUMN id SET DEFAULT nextval('public.student_parent_note_reads_id_seq'::regclass);


--
-- Name: student_parent_note_replies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_replies ALTER COLUMN id SET DEFAULT nextval('public.student_parent_note_replies_id_seq'::regclass);


--
-- Name: student_parent_notes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_notes ALTER COLUMN id SET DEFAULT nextval('public.student_parent_notes_id_seq'::regclass);


--
-- Name: student_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_profiles ALTER COLUMN id SET DEFAULT nextval('public.student_profiles_id_seq'::regclass);


--
-- Name: student_routine_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_routine_profiles ALTER COLUMN id SET DEFAULT nextval('public.student_routine_profiles_id_seq'::regclass);


--
-- Name: student_schedules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_schedules ALTER COLUMN id SET DEFAULT nextval('public.student_schedules_id_seq'::regclass);


--
-- Name: student_study_streaks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_study_streaks ALTER COLUMN id SET DEFAULT nextval('public.student_study_streaks_id_seq'::regclass);


--
-- Name: student_subject_choices id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_subject_choices ALTER COLUMN id SET DEFAULT nextval('public.student_subject_choices_id_seq'::regclass);


--
-- Name: student_teacher_choices id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_teacher_choices ALTER COLUMN id SET DEFAULT nextval('public.student_teacher_choices_id_seq'::regclass);


--
-- Name: student_xp id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_xp ALTER COLUMN id SET DEFAULT nextval('public.student_xp_id_seq'::regclass);


--
-- Name: study_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions ALTER COLUMN id SET DEFAULT nextval('public.study_sessions_id_seq'::regclass);


--
-- Name: subjects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects ALTER COLUMN id SET DEFAULT nextval('public.subjects_id_seq'::regclass);


--
-- Name: teacher_achievements id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_achievements ALTER COLUMN id SET DEFAULT nextval('public.teacher_achievements_id_seq'::regclass);


--
-- Name: teacher_professional_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_professional_documents ALTER COLUMN id SET DEFAULT nextval('public.teacher_professional_documents_id_seq'::regclass);


--
-- Name: teacher_profile_grades id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_grades ALTER COLUMN id SET DEFAULT nextval('public.teacher_profile_grades_id_seq'::regclass);


--
-- Name: teacher_profile_subjects id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_subjects ALTER COLUMN id SET DEFAULT nextval('public.teacher_profile_subjects_id_seq'::regclass);


--
-- Name: teacher_profiles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profiles ALTER COLUMN id SET DEFAULT nextval('public.teacher_profiles_id_seq'::regclass);


--
-- Name: teacher_qualifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_qualifications ALTER COLUMN id SET DEFAULT nextval('public.teacher_qualifications_id_seq'::regclass);


--
-- Name: teacher_student_notes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_student_notes ALTER COLUMN id SET DEFAULT nextval('public.teacher_student_notes_id_seq'::regclass);


--
-- Name: teacher_teaching_experiences id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_teaching_experiences ALTER COLUMN id SET DEFAULT nextval('public.teacher_teaching_experiences_id_seq'::regclass);


--
-- Name: teacher_voice_samples id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_voice_samples ALTER COLUMN id SET DEFAULT nextval('public.teacher_voice_samples_id_seq'::regclass);


--
-- Name: teacher_why_study_points id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_why_study_points ALTER COLUMN id SET DEFAULT nextval('public.teacher_why_study_points_id_seq'::regclass);


--
-- Name: two_factor_challenges id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.two_factor_challenges ALTER COLUMN id SET DEFAULT nextval('public.two_factor_challenges_id_seq'::regclass);


--
-- Name: user_roles id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles ALTER COLUMN id SET DEFAULT nextval('public.user_roles_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: ai_jobs ai_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_jobs
    ADD CONSTRAINT ai_jobs_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: auth_sessions auth_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_pkey PRIMARY KEY (id);


--
-- Name: auth_sessions auth_sessions_refresh_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_refresh_token_hash_key UNIQUE (refresh_token_hash);


--
-- Name: availability_blocks availability_blocks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availability_blocks
    ADD CONSTRAINT availability_blocks_pkey PRIMARY KEY (id);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: content_chunks content_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_chunks
    ADD CONSTRAINT content_chunks_pkey PRIMARY KEY (id);


--
-- Name: conversation_message_reads conversation_message_reads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message_reads
    ADD CONSTRAINT conversation_message_reads_pkey PRIMARY KEY (id);


--
-- Name: conversation_messages conversation_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_messages
    ADD CONSTRAINT conversation_messages_pkey PRIMARY KEY (id);


--
-- Name: conversation_participants conversation_participants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT conversation_participants_pkey PRIMARY KEY (id);


--
-- Name: conversation_threads conversation_threads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_threads
    ADD CONSTRAINT conversation_threads_pkey PRIMARY KEY (id);


--
-- Name: course_analytics course_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_analytics
    ADD CONSTRAINT course_analytics_pkey PRIMARY KEY (course_id);


--
-- Name: course_quiz_answers course_quiz_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_answers
    ADD CONSTRAINT course_quiz_answers_pkey PRIMARY KEY (id);


--
-- Name: course_quiz_attempts course_quiz_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_attempts
    ADD CONSTRAINT course_quiz_attempts_pkey PRIMARY KEY (id);


--
-- Name: course_quiz_questions course_quiz_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_questions
    ADD CONSTRAINT course_quiz_questions_pkey PRIMARY KEY (id);


--
-- Name: course_quizzes course_quizzes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quizzes
    ADD CONSTRAINT course_quizzes_pkey PRIMARY KEY (id);


--
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- Name: email_tokens email_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_tokens
    ADD CONSTRAINT email_tokens_pkey PRIMARY KEY (id);


--
-- Name: exams exams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_pkey PRIMARY KEY (id);


--
-- Name: language_activity_log language_activity_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_activity_log
    ADD CONSTRAINT language_activity_log_pkey PRIMARY KEY (id);


--
-- Name: language_ai_usage language_ai_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_ai_usage
    ADD CONSTRAINT language_ai_usage_pkey PRIMARY KEY (id);


--
-- Name: language_analytics language_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_analytics
    ADD CONSTRAINT language_analytics_pkey PRIMARY KEY (student_id, language_id);


--
-- Name: language_assessment_skill_scores language_assessment_skill_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessment_skill_scores
    ADD CONSTRAINT language_assessment_skill_scores_pkey PRIMARY KEY (id);


--
-- Name: language_assessments language_assessments_attempt_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessments
    ADD CONSTRAINT language_assessments_attempt_id_key UNIQUE (attempt_id);


--
-- Name: language_assessments language_assessments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessments
    ADD CONSTRAINT language_assessments_pkey PRIMARY KEY (id);


--
-- Name: language_certificates language_certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_certificates
    ADD CONSTRAINT language_certificates_pkey PRIMARY KEY (id);


--
-- Name: language_component_mastery language_component_mastery_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_component_mastery
    ADD CONSTRAINT language_component_mastery_pkey PRIMARY KEY (id);


--
-- Name: language_content_items language_content_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_content_items
    ADD CONSTRAINT language_content_items_pkey PRIMARY KEY (id);


--
-- Name: language_conversation_scenarios language_conversation_scenarios_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_conversation_scenarios
    ADD CONSTRAINT language_conversation_scenarios_pkey PRIMARY KEY (id);


--
-- Name: language_curriculum_progress language_curriculum_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_curriculum_progress
    ADD CONSTRAINT language_curriculum_progress_pkey PRIMARY KEY (id);


--
-- Name: language_error_patterns language_error_patterns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_error_patterns
    ADD CONSTRAINT language_error_patterns_pkey PRIMARY KEY (id);


--
-- Name: language_exam_sessions language_exam_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_exam_sessions
    ADD CONSTRAINT language_exam_sessions_pkey PRIMARY KEY (id);


--
-- Name: language_generated_questions language_generated_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_generated_questions
    ADD CONSTRAINT language_generated_questions_pkey PRIMARY KEY (id);


--
-- Name: language_knowledge_components language_knowledge_components_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_knowledge_components
    ADD CONSTRAINT language_knowledge_components_pkey PRIMARY KEY (id);


--
-- Name: language_learning_paths language_learning_paths_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_learning_paths
    ADD CONSTRAINT language_learning_paths_pkey PRIMARY KEY (id);


--
-- Name: language_lesson_audio_cache language_lesson_audio_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_lesson_audio_cache
    ADD CONSTRAINT language_lesson_audio_cache_pkey PRIMARY KEY (id);


--
-- Name: language_listening_progress language_listening_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_listening_progress
    ADD CONSTRAINT language_listening_progress_pkey PRIMARY KEY (id);


--
-- Name: language_path_items language_path_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_path_items
    ADD CONSTRAINT language_path_items_pkey PRIMARY KEY (id);


--
-- Name: language_placement_attempts language_placement_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_attempts
    ADD CONSTRAINT language_placement_attempts_pkey PRIMARY KEY (id);


--
-- Name: language_placement_questions language_placement_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_questions
    ADD CONSTRAINT language_placement_questions_pkey PRIMARY KEY (id);


--
-- Name: language_placement_responses language_placement_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_responses
    ADD CONSTRAINT language_placement_responses_pkey PRIMARY KEY (id);


--
-- Name: language_placement_sections language_placement_sections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_sections
    ADD CONSTRAINT language_placement_sections_pkey PRIMARY KEY (id);


--
-- Name: language_products language_products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_products
    ADD CONSTRAINT language_products_pkey PRIMARY KEY (id);


--
-- Name: language_progress_snapshots language_progress_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_progress_snapshots
    ADD CONSTRAINT language_progress_snapshots_pkey PRIMARY KEY (id);


--
-- Name: language_pronunciation_scores language_pronunciation_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_pronunciation_scores
    ADD CONSTRAINT language_pronunciation_scores_pkey PRIMARY KEY (id);


--
-- Name: language_reading_progress language_reading_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_reading_progress
    ADD CONSTRAINT language_reading_progress_pkey PRIMARY KEY (id);


--
-- Name: language_scenario_progress language_scenario_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_scenario_progress
    ADD CONSTRAINT language_scenario_progress_pkey PRIMARY KEY (id);


--
-- Name: language_skill_level_state language_skill_level_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_skill_level_state
    ADD CONSTRAINT language_skill_level_state_pkey PRIMARY KEY (id);


--
-- Name: language_speaking_conversation_sessions language_speaking_conversation_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_sessions
    ADD CONSTRAINT language_speaking_conversation_sessions_pkey PRIMARY KEY (id);


--
-- Name: language_speaking_conversation_turns language_speaking_conversation_turns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_turns
    ADD CONSTRAINT language_speaking_conversation_turns_pkey PRIMARY KEY (id);


--
-- Name: language_speaking_progress language_speaking_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_progress
    ADD CONSTRAINT language_speaking_progress_pkey PRIMARY KEY (id);


--
-- Name: language_streaks language_streaks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_streaks
    ADD CONSTRAINT language_streaks_pkey PRIMARY KEY (id);


--
-- Name: language_student_achievements language_student_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_achievements
    ADD CONSTRAINT language_student_achievements_pkey PRIMARY KEY (id);


--
-- Name: language_student_profiles language_student_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_profiles
    ADD CONSTRAINT language_student_profiles_pkey PRIMARY KEY (id);


--
-- Name: language_subscriptions language_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_subscriptions
    ADD CONSTRAINT language_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: language_vocabulary_catalog language_vocabulary_catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog
    ADD CONSTRAINT language_vocabulary_catalog_pkey PRIMARY KEY (id);


--
-- Name: language_vocabulary_catalog_seen language_vocabulary_catalog_seen_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog_seen
    ADD CONSTRAINT language_vocabulary_catalog_seen_pkey PRIMARY KEY (id);


--
-- Name: language_vocabulary_progress language_vocabulary_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_progress
    ADD CONSTRAINT language_vocabulary_progress_pkey PRIMARY KEY (id);


--
-- Name: language_writing_progress language_writing_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_writing_progress
    ADD CONSTRAINT language_writing_progress_pkey PRIMARY KEY (id);


--
-- Name: languages languages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.languages
    ADD CONSTRAINT languages_pkey PRIMARY KEY (id);


--
-- Name: lesson_assets lesson_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_assets
    ADD CONSTRAINT lesson_assets_pkey PRIMARY KEY (id);


--
-- Name: lessons lessons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lessons
    ADD CONSTRAINT lessons_pkey PRIMARY KEY (id);


--
-- Name: media_objects media_objects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_objects
    ADD CONSTRAINT media_objects_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: parent_notification_settings parent_notification_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notification_settings
    ADD CONSTRAINT parent_notification_settings_pkey PRIMARY KEY (id);


--
-- Name: parent_student_links parent_student_links_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student_links
    ADD CONSTRAINT parent_student_links_pkey PRIMARY KEY (id);


--
-- Name: payment_items payment_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_items
    ADD CONSTRAINT payment_items_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: planner_chat_messages planner_chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_chat_messages
    ADD CONSTRAINT planner_chat_messages_pkey PRIMARY KEY (id);


--
-- Name: planner_life_events planner_life_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_life_events
    ADD CONSTRAINT planner_life_events_pkey PRIMARY KEY (id);


--
-- Name: planner_profiles planner_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_profiles
    ADD CONSTRAINT planner_profiles_pkey PRIMARY KEY (id);


--
-- Name: planner_schedule_slots planner_schedule_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_schedule_slots
    ADD CONSTRAINT planner_schedule_slots_pkey PRIMARY KEY (id);


--
-- Name: quiz_attempts quiz_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_pkey PRIMARY KEY (id);


--
-- Name: quiz_questions quiz_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quiz_questions
    ADD CONSTRAINT quiz_questions_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: roles roles_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_slug_key UNIQUE (slug);


--
-- Name: routine_slots routine_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.routine_slots
    ADD CONSTRAINT routine_slots_pkey PRIMARY KEY (id);


--
-- Name: schedule_optimization_logs schedule_optimization_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_optimization_logs
    ADD CONSTRAINT schedule_optimization_logs_pkey PRIMARY KEY (id);


--
-- Name: student_achievements student_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_achievements
    ADD CONSTRAINT student_achievements_pkey PRIMARY KEY (id);


--
-- Name: student_activity_events student_activity_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_activity_events
    ADD CONSTRAINT student_activity_events_pkey PRIMARY KEY (id);


--
-- Name: student_activity_sessions student_activity_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_activity_sessions
    ADD CONSTRAINT student_activity_sessions_pkey PRIMARY KEY (id);


--
-- Name: student_analytics student_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_analytics
    ADD CONSTRAINT student_analytics_pkey PRIMARY KEY (student_id);


--
-- Name: student_attendance_records student_attendance_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_attendance_records
    ADD CONSTRAINT student_attendance_records_pkey PRIMARY KEY (id);


--
-- Name: student_course_access student_course_access_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_course_access
    ADD CONSTRAINT student_course_access_pkey PRIMARY KEY (id);


--
-- Name: student_engagement_events student_engagement_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_engagement_events
    ADD CONSTRAINT student_engagement_events_pkey PRIMARY KEY (id);


--
-- Name: student_grade_reports student_grade_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_grade_reports
    ADD CONSTRAINT student_grade_reports_pkey PRIMARY KEY (id);


--
-- Name: student_learning_profiles student_learning_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_learning_profiles
    ADD CONSTRAINT student_learning_profiles_pkey PRIMARY KEY (id);


--
-- Name: student_lesson_progress student_lesson_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_lesson_progress
    ADD CONSTRAINT student_lesson_progress_pkey PRIMARY KEY (id);


--
-- Name: student_parent_note_reads student_parent_note_reads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_reads
    ADD CONSTRAINT student_parent_note_reads_pkey PRIMARY KEY (id);


--
-- Name: student_parent_note_replies student_parent_note_replies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_replies
    ADD CONSTRAINT student_parent_note_replies_pkey PRIMARY KEY (id);


--
-- Name: student_parent_notes student_parent_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_notes
    ADD CONSTRAINT student_parent_notes_pkey PRIMARY KEY (id);


--
-- Name: student_profiles student_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_profiles
    ADD CONSTRAINT student_profiles_pkey PRIMARY KEY (id);


--
-- Name: student_profiles student_profiles_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_profiles
    ADD CONSTRAINT student_profiles_user_id_key UNIQUE (user_id);


--
-- Name: student_routine_profiles student_routine_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_routine_profiles
    ADD CONSTRAINT student_routine_profiles_pkey PRIMARY KEY (id);


--
-- Name: student_schedules student_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_schedules
    ADD CONSTRAINT student_schedules_pkey PRIMARY KEY (id);


--
-- Name: student_study_streaks student_study_streaks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_study_streaks
    ADD CONSTRAINT student_study_streaks_pkey PRIMARY KEY (id);


--
-- Name: student_subject_choices student_subject_choices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_subject_choices
    ADD CONSTRAINT student_subject_choices_pkey PRIMARY KEY (id);


--
-- Name: student_teacher_choices student_teacher_choices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_teacher_choices
    ADD CONSTRAINT student_teacher_choices_pkey PRIMARY KEY (id);


--
-- Name: student_xp student_xp_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_xp
    ADD CONSTRAINT student_xp_pkey PRIMARY KEY (id);


--
-- Name: study_sessions study_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions
    ADD CONSTRAINT study_sessions_pkey PRIMARY KEY (id);


--
-- Name: subjects subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT subjects_pkey PRIMARY KEY (id);


--
-- Name: teacher_achievements teacher_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_achievements
    ADD CONSTRAINT teacher_achievements_pkey PRIMARY KEY (id);


--
-- Name: teacher_analytics teacher_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_analytics
    ADD CONSTRAINT teacher_analytics_pkey PRIMARY KEY (teacher_profile_id);


--
-- Name: teacher_professional_documents teacher_professional_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_professional_documents
    ADD CONSTRAINT teacher_professional_documents_pkey PRIMARY KEY (id);


--
-- Name: teacher_profile_grades teacher_profile_grades_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_grades
    ADD CONSTRAINT teacher_profile_grades_pkey PRIMARY KEY (id);


--
-- Name: teacher_profile_subjects teacher_profile_subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_subjects
    ADD CONSTRAINT teacher_profile_subjects_pkey PRIMARY KEY (id);


--
-- Name: teacher_profiles teacher_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profiles
    ADD CONSTRAINT teacher_profiles_pkey PRIMARY KEY (id);


--
-- Name: teacher_qualifications teacher_qualifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_qualifications
    ADD CONSTRAINT teacher_qualifications_pkey PRIMARY KEY (id);


--
-- Name: teacher_student_notes teacher_student_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_student_notes
    ADD CONSTRAINT teacher_student_notes_pkey PRIMARY KEY (id);


--
-- Name: teacher_teaching_experiences teacher_teaching_experiences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_teaching_experiences
    ADD CONSTRAINT teacher_teaching_experiences_pkey PRIMARY KEY (id);


--
-- Name: teacher_voice_samples teacher_voice_samples_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_voice_samples
    ADD CONSTRAINT teacher_voice_samples_pkey PRIMARY KEY (id);


--
-- Name: teacher_why_study_points teacher_why_study_points_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_why_study_points
    ADD CONSTRAINT teacher_why_study_points_pkey PRIMARY KEY (id);


--
-- Name: two_factor_challenges two_factor_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.two_factor_challenges
    ADD CONSTRAINT two_factor_challenges_pkey PRIMARY KEY (id);


--
-- Name: conversation_message_reads uq_conversation_message_read; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message_reads
    ADD CONSTRAINT uq_conversation_message_read UNIQUE (message_id, user_id);


--
-- Name: conversation_participants uq_conversation_participant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT uq_conversation_participant UNIQUE (thread_id, user_id);


--
-- Name: course_quiz_answers uq_course_quiz_answer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_answers
    ADD CONSTRAINT uq_course_quiz_answer UNIQUE (attempt_id, question_id);


--
-- Name: course_quiz_attempts uq_course_quiz_attempt; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_attempts
    ADD CONSTRAINT uq_course_quiz_attempt UNIQUE (quiz_id, student_id);


--
-- Name: email_tokens uq_email_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_tokens
    ADD CONSTRAINT uq_email_tokens_token_hash UNIQUE (token_hash);


--
-- Name: language_conversation_scenarios uq_lang_conversation_scenario_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_conversation_scenarios
    ADD CONSTRAINT uq_lang_conversation_scenario_key UNIQUE (language_id, scenario_key);


--
-- Name: language_component_mastery uq_language_component_mastery; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_component_mastery
    ADD CONSTRAINT uq_language_component_mastery UNIQUE (student_id, language_id, component_id);


--
-- Name: language_curriculum_progress uq_language_curriculum_progress; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_curriculum_progress
    ADD CONSTRAINT uq_language_curriculum_progress UNIQUE (student_id, objective_id);


--
-- Name: language_error_patterns uq_language_error_pattern; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_error_patterns
    ADD CONSTRAINT uq_language_error_pattern UNIQUE (student_id, language_id, pattern_key);


--
-- Name: language_lesson_audio_cache uq_language_lesson_audio_cache; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_lesson_audio_cache
    ADD CONSTRAINT uq_language_lesson_audio_cache UNIQUE (content_item_id, voice_source, teacher_id);


--
-- Name: language_listening_progress uq_language_listening_progress; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_listening_progress
    ADD CONSTRAINT uq_language_listening_progress UNIQUE (student_id, content_item_id);


--
-- Name: language_placement_responses uq_language_placement_attempt_question; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_responses
    ADD CONSTRAINT uq_language_placement_attempt_question UNIQUE (attempt_id, question_id);


--
-- Name: language_progress_snapshots uq_language_progress_snapshot; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_progress_snapshots
    ADD CONSTRAINT uq_language_progress_snapshot UNIQUE (student_id, language_id, snapshot_date);


--
-- Name: language_reading_progress uq_language_reading_progress; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_reading_progress
    ADD CONSTRAINT uq_language_reading_progress UNIQUE (student_id, content_item_id);


--
-- Name: language_scenario_progress uq_language_scenario_progress_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_scenario_progress
    ADD CONSTRAINT uq_language_scenario_progress_key UNIQUE (student_id, language_id, scenario_key);


--
-- Name: language_skill_level_state uq_language_skill_level_state; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_skill_level_state
    ADD CONSTRAINT uq_language_skill_level_state UNIQUE (student_id, language_id, skill);


--
-- Name: language_speaking_progress uq_language_speaking_progress; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_progress
    ADD CONSTRAINT uq_language_speaking_progress UNIQUE (student_id, content_item_id);


--
-- Name: language_streaks uq_language_streak; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_streaks
    ADD CONSTRAINT uq_language_streak UNIQUE (student_id, language_id);


--
-- Name: language_student_achievements uq_language_student_achievement; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_achievements
    ADD CONSTRAINT uq_language_student_achievement UNIQUE (student_id, language_id, achievement_key);


--
-- Name: language_student_profiles uq_language_student_profile; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_profiles
    ADD CONSTRAINT uq_language_student_profile UNIQUE (student_id, language_id);


--
-- Name: language_subscriptions uq_language_subscription_student_product; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_subscriptions
    ADD CONSTRAINT uq_language_subscription_student_product UNIQUE (student_id, product_id);


--
-- Name: language_vocabulary_progress uq_language_vocab; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_progress
    ADD CONSTRAINT uq_language_vocab UNIQUE (student_id, language_id, lemma);


--
-- Name: language_vocabulary_catalog_seen uq_language_vocabulary_catalog_seen; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog_seen
    ADD CONSTRAINT uq_language_vocabulary_catalog_seen UNIQUE (student_id, catalog_id);


--
-- Name: language_vocabulary_catalog uq_language_vocabulary_catalog_word_level; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog
    ADD CONSTRAINT uq_language_vocabulary_catalog_word_level UNIQUE (word, cefr_level);


--
-- Name: language_writing_progress uq_language_writing_progress; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_writing_progress
    ADD CONSTRAINT uq_language_writing_progress UNIQUE (student_id, content_item_id);


--
-- Name: student_parent_note_reads uq_parent_note_read; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_reads
    ADD CONSTRAINT uq_parent_note_read UNIQUE (note_id, parent_id);


--
-- Name: parent_notification_settings uq_parent_notification_settings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notification_settings
    ADD CONSTRAINT uq_parent_notification_settings UNIQUE (parent_id, student_id);


--
-- Name: parent_student_links uq_parent_student; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student_links
    ADD CONSTRAINT uq_parent_student UNIQUE (parent_id, student_id);


--
-- Name: student_achievements uq_student_achievement; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_achievements
    ADD CONSTRAINT uq_student_achievement UNIQUE (student_id, achievement_key);


--
-- Name: student_attendance_records uq_student_attendance_date; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_attendance_records
    ADD CONSTRAINT uq_student_attendance_date UNIQUE (student_id, date);


--
-- Name: student_course_access uq_student_course; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_course_access
    ADD CONSTRAINT uq_student_course UNIQUE (student_id, course_id);


--
-- Name: student_grade_reports uq_student_grade_report; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_grade_reports
    ADD CONSTRAINT uq_student_grade_report UNIQUE (student_id, course_id);


--
-- Name: student_learning_profiles uq_student_learning_profiles_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_learning_profiles
    ADD CONSTRAINT uq_student_learning_profiles_user_id UNIQUE (user_id);


--
-- Name: student_lesson_progress uq_student_lesson_progress; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_lesson_progress
    ADD CONSTRAINT uq_student_lesson_progress UNIQUE (student_id, lesson_id);


--
-- Name: student_routine_profiles uq_student_routine_profiles_student_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_routine_profiles
    ADD CONSTRAINT uq_student_routine_profiles_student_id UNIQUE (student_id);


--
-- Name: student_study_streaks uq_student_study_streaks_student; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_study_streaks
    ADD CONSTRAINT uq_student_study_streaks_student UNIQUE (student_id);


--
-- Name: student_subject_choices uq_student_subject; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_subject_choices
    ADD CONSTRAINT uq_student_subject UNIQUE (student_id, subject_id);


--
-- Name: student_teacher_choices uq_student_teacher_subject; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_teacher_choices
    ADD CONSTRAINT uq_student_teacher_subject UNIQUE (student_id, subject_id);


--
-- Name: student_xp uq_student_xp_student; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_xp
    ADD CONSTRAINT uq_student_xp_student UNIQUE (student_id);


--
-- Name: subjects uq_subject_grade_slug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subjects
    ADD CONSTRAINT uq_subject_grade_slug UNIQUE (grade, slug);


--
-- Name: teacher_profile_grades uq_teacher_grade; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_grades
    ADD CONSTRAINT uq_teacher_grade UNIQUE (teacher_profile_id, grade);


--
-- Name: teacher_profile_subjects uq_teacher_subject; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_subjects
    ADD CONSTRAINT uq_teacher_subject UNIQUE (teacher_profile_id, subject_id);


--
-- Name: user_roles uq_user_role; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT uq_user_role UNIQUE (user_id, role_id);


--
-- Name: user_roles user_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_ai_jobs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_jobs_created_at ON public.ai_jobs USING btree (created_at);


--
-- Name: ix_ai_jobs_job_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_jobs_job_type ON public.ai_jobs USING btree (job_type);


--
-- Name: ix_ai_jobs_lesson_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_jobs_lesson_id ON public.ai_jobs USING btree (lesson_id);


--
-- Name: ix_ai_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_jobs_status ON public.ai_jobs USING btree (status);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_actor_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_actor_user_id ON public.audit_logs USING btree (actor_user_id);


--
-- Name: ix_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: ix_audit_logs_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_entity_id ON public.audit_logs USING btree (entity_id);


--
-- Name: ix_audit_logs_entity_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_entity_type ON public.audit_logs USING btree (entity_type);


--
-- Name: ix_auth_sessions_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_sessions_expires_at ON public.auth_sessions USING btree (expires_at);


--
-- Name: ix_auth_sessions_revoked_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_sessions_revoked_at ON public.auth_sessions USING btree (revoked_at);


--
-- Name: ix_auth_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_auth_sessions_user_id ON public.auth_sessions USING btree (user_id);


--
-- Name: ix_availability_blocks_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_availability_blocks_student_id ON public.availability_blocks USING btree (student_id);


--
-- Name: ix_chat_messages_lesson_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_lesson_id ON public.chat_messages USING btree (lesson_id);


--
-- Name: ix_chat_messages_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_messages_student_id ON public.chat_messages USING btree (student_id);


--
-- Name: ix_content_chunks_lesson_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_content_chunks_lesson_id ON public.content_chunks USING btree (lesson_id);


--
-- Name: ix_conversation_message_reads_message_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_message_reads_message_id ON public.conversation_message_reads USING btree (message_id);


--
-- Name: ix_conversation_messages_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_messages_created_at ON public.conversation_messages USING btree (created_at);


--
-- Name: ix_conversation_messages_thread_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_messages_thread_id ON public.conversation_messages USING btree (thread_id);


--
-- Name: ix_conversation_participants_thread_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_participants_thread_id ON public.conversation_participants USING btree (thread_id);


--
-- Name: ix_conversation_participants_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_participants_user_id ON public.conversation_participants USING btree (user_id);


--
-- Name: ix_conversation_threads_last_message_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_threads_last_message_at ON public.conversation_threads USING btree (last_message_at);


--
-- Name: ix_conversation_threads_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_threads_student_id ON public.conversation_threads USING btree (student_id);


--
-- Name: ix_conversation_threads_thread_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conversation_threads_thread_type ON public.conversation_threads USING btree (thread_type);


--
-- Name: ix_course_quiz_answers_attempt_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_course_quiz_answers_attempt_id ON public.course_quiz_answers USING btree (attempt_id);


--
-- Name: ix_course_quiz_attempts_quiz_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_course_quiz_attempts_quiz_id ON public.course_quiz_attempts USING btree (quiz_id);


--
-- Name: ix_course_quiz_attempts_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_course_quiz_attempts_student_id ON public.course_quiz_attempts USING btree (student_id);


--
-- Name: ix_course_quiz_questions_quiz_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_course_quiz_questions_quiz_id ON public.course_quiz_questions USING btree (quiz_id);


--
-- Name: ix_course_quizzes_course_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_course_quizzes_course_id ON public.course_quizzes USING btree (course_id);


--
-- Name: ix_courses_grade; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_courses_grade ON public.courses USING btree (grade);


--
-- Name: ix_courses_subject_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_courses_subject_id ON public.courses USING btree (subject_id);


--
-- Name: ix_courses_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_courses_teacher_profile_id ON public.courses USING btree (teacher_profile_id);


--
-- Name: ix_email_tokens_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_tokens_expires_at ON public.email_tokens USING btree (expires_at);


--
-- Name: ix_email_tokens_purpose; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_tokens_purpose ON public.email_tokens USING btree (purpose);


--
-- Name: ix_email_tokens_used_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_tokens_used_at ON public.email_tokens USING btree (used_at);


--
-- Name: ix_email_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_email_tokens_user_id ON public.email_tokens USING btree (user_id);


--
-- Name: ix_exams_exam_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_exams_exam_at ON public.exams USING btree (exam_at);


--
-- Name: ix_exams_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_exams_student_id ON public.exams USING btree (student_id);


--
-- Name: ix_language_activity_log_student_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_activity_log_student_created ON public.language_activity_log USING btree (student_id, created_at);


--
-- Name: ix_language_ai_usage_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_ai_usage_created_at ON public.language_ai_usage USING btree (created_at);


--
-- Name: ix_language_certificates_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_language_certificates_code ON public.language_certificates USING btree (verification_code);


--
-- Name: ix_language_certificates_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_language_certificates_number ON public.language_certificates USING btree (certificate_number);


--
-- Name: ix_language_certificates_student_language; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_certificates_student_language ON public.language_certificates USING btree (student_id, language_id);


--
-- Name: ix_language_component_mastery_component_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_component_mastery_component_id ON public.language_component_mastery USING btree (component_id);


--
-- Name: ix_language_component_mastery_language_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_component_mastery_language_id ON public.language_component_mastery USING btree (language_id);


--
-- Name: ix_language_component_mastery_next_review_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_component_mastery_next_review_at ON public.language_component_mastery USING btree (next_review_at);


--
-- Name: ix_language_component_mastery_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_component_mastery_student_id ON public.language_component_mastery USING btree (student_id);


--
-- Name: ix_language_curriculum_progress_language_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_curriculum_progress_language_id ON public.language_curriculum_progress USING btree (language_id);


--
-- Name: ix_language_curriculum_progress_objective_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_curriculum_progress_objective_id ON public.language_curriculum_progress USING btree (objective_id);


--
-- Name: ix_language_curriculum_progress_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_curriculum_progress_student_id ON public.language_curriculum_progress USING btree (student_id);


--
-- Name: ix_language_error_patterns_language_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_error_patterns_language_id ON public.language_error_patterns USING btree (language_id);


--
-- Name: ix_language_error_patterns_pattern_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_error_patterns_pattern_key ON public.language_error_patterns USING btree (pattern_key);


--
-- Name: ix_language_error_patterns_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_error_patterns_student_id ON public.language_error_patterns USING btree (student_id);


--
-- Name: ix_language_exam_sessions_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_exam_sessions_student_id ON public.language_exam_sessions USING btree (student_id);


--
-- Name: ix_language_generated_questions_component_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_generated_questions_component_code ON public.language_generated_questions USING btree (component_code);


--
-- Name: ix_language_generated_questions_language_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_generated_questions_language_id ON public.language_generated_questions USING btree (language_id);


--
-- Name: ix_language_knowledge_components_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_language_knowledge_components_code ON public.language_knowledge_components USING btree (code);


--
-- Name: ix_language_lesson_audio_cache_content_item_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_lesson_audio_cache_content_item_id ON public.language_lesson_audio_cache USING btree (content_item_id);


--
-- Name: ix_language_products_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_language_products_slug ON public.language_products USING btree (slug);


--
-- Name: ix_language_progress_snapshots_language_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_progress_snapshots_language_id ON public.language_progress_snapshots USING btree (language_id);


--
-- Name: ix_language_progress_snapshots_snapshot_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_progress_snapshots_snapshot_date ON public.language_progress_snapshots USING btree (snapshot_date);


--
-- Name: ix_language_progress_snapshots_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_progress_snapshots_student_id ON public.language_progress_snapshots USING btree (student_id);


--
-- Name: ix_language_pronunciation_scores_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_pronunciation_scores_created_at ON public.language_pronunciation_scores USING btree (created_at);


--
-- Name: ix_language_pronunciation_scores_language_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_pronunciation_scores_language_id ON public.language_pronunciation_scores USING btree (language_id);


--
-- Name: ix_language_pronunciation_scores_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_pronunciation_scores_student_id ON public.language_pronunciation_scores USING btree (student_id);


--
-- Name: ix_language_scenario_progress_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_scenario_progress_student ON public.language_scenario_progress USING btree (student_id, language_id);


--
-- Name: ix_language_skill_level_state_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_skill_level_state_student_id ON public.language_skill_level_state USING btree (student_id);


--
-- Name: ix_language_speaking_conversation_sessions_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_speaking_conversation_sessions_student ON public.language_speaking_conversation_sessions USING btree (student_id, language_id, status);


--
-- Name: ix_language_speaking_conversation_turns_session; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_speaking_conversation_turns_session ON public.language_speaking_conversation_turns USING btree (session_id, turn_index);


--
-- Name: ix_language_speaking_conversation_turns_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_speaking_conversation_turns_student ON public.language_speaking_conversation_turns USING btree (student_id, created_at);


--
-- Name: ix_language_student_achievements_student; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_student_achievements_student ON public.language_student_achievements USING btree (student_id, language_id);


--
-- Name: ix_language_subscriptions_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_subscriptions_expires_at ON public.language_subscriptions USING btree (expires_at);


--
-- Name: ix_language_subscriptions_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_subscriptions_student_id ON public.language_subscriptions USING btree (student_id);


--
-- Name: ix_language_vocabulary_catalog_cefr_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_vocabulary_catalog_cefr_level ON public.language_vocabulary_catalog USING btree (cefr_level);


--
-- Name: ix_language_vocabulary_catalog_context_theme; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_vocabulary_catalog_context_theme ON public.language_vocabulary_catalog USING btree (context_theme);


--
-- Name: ix_language_vocabulary_catalog_seen_catalog_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_vocabulary_catalog_seen_catalog_id ON public.language_vocabulary_catalog_seen USING btree (catalog_id);


--
-- Name: ix_language_vocabulary_catalog_seen_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_vocabulary_catalog_seen_student_id ON public.language_vocabulary_catalog_seen USING btree (student_id);


--
-- Name: ix_language_vocabulary_catalog_word; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_language_vocabulary_catalog_word ON public.language_vocabulary_catalog USING btree (word);


--
-- Name: ix_languages_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_languages_code ON public.languages USING btree (code);


--
-- Name: ix_lesson_assets_lesson_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lesson_assets_lesson_id ON public.lesson_assets USING btree (lesson_id);


--
-- Name: ix_lesson_assets_media_object_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lesson_assets_media_object_id ON public.lesson_assets USING btree (media_object_id);


--
-- Name: ix_lesson_assets_sort_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lesson_assets_sort_order ON public.lesson_assets USING btree (lesson_id, sort_order);


--
-- Name: ix_lessons_course_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lessons_course_id ON public.lessons USING btree (course_id);


--
-- Name: ix_lessons_teacher_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lessons_teacher_id ON public.lessons USING btree (teacher_id);


--
-- Name: ix_media_objects_storage_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_media_objects_storage_key ON public.media_objects USING btree (storage_key);


--
-- Name: ix_media_objects_storage_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_media_objects_storage_provider ON public.media_objects USING btree (storage_provider);


--
-- Name: ix_notifications_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_created_at ON public.notifications USING btree (created_at);


--
-- Name: ix_notifications_is_read; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_is_read ON public.notifications USING btree (is_read);


--
-- Name: ix_notifications_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_type ON public.notifications USING btree (type);


--
-- Name: ix_notifications_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_user_id ON public.notifications USING btree (user_id);


--
-- Name: ix_parent_notification_settings_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_parent_notification_settings_parent_id ON public.parent_notification_settings USING btree (parent_id);


--
-- Name: ix_parent_notification_settings_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_parent_notification_settings_student_id ON public.parent_notification_settings USING btree (student_id);


--
-- Name: ix_parent_student_links_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_parent_student_links_parent_id ON public.parent_student_links USING btree (parent_id);


--
-- Name: ix_parent_student_links_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_parent_student_links_student_id ON public.parent_student_links USING btree (student_id);


--
-- Name: ix_payment_items_course_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_items_course_id ON public.payment_items USING btree (course_id);


--
-- Name: ix_payment_items_payment_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_items_payment_id ON public.payment_items USING btree (payment_id);


--
-- Name: ix_payments_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_student_id ON public.payments USING btree (student_id);


--
-- Name: ix_planner_chat_messages_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_planner_chat_messages_student_id ON public.planner_chat_messages USING btree (student_id);


--
-- Name: ix_planner_life_events_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_planner_life_events_student_id ON public.planner_life_events USING btree (student_id);


--
-- Name: ix_planner_profiles_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_planner_profiles_student_id ON public.planner_profiles USING btree (student_id);


--
-- Name: ix_planner_schedule_slots_scheduled_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_planner_schedule_slots_scheduled_at ON public.planner_schedule_slots USING btree (scheduled_at);


--
-- Name: ix_planner_schedule_slots_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_planner_schedule_slots_student_id ON public.planner_schedule_slots USING btree (student_id);


--
-- Name: ix_quiz_attempts_lesson_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quiz_attempts_lesson_id ON public.quiz_attempts USING btree (lesson_id);


--
-- Name: ix_quiz_attempts_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quiz_attempts_student_id ON public.quiz_attempts USING btree (student_id);


--
-- Name: ix_quiz_questions_lesson_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_quiz_questions_lesson_id ON public.quiz_questions USING btree (lesson_id);


--
-- Name: ix_roles_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_roles_slug ON public.roles USING btree (slug);


--
-- Name: ix_routine_slots_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_routine_slots_profile_id ON public.routine_slots USING btree (profile_id);


--
-- Name: ix_schedule_optimization_logs_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_schedule_optimization_logs_event_type ON public.schedule_optimization_logs USING btree (event_type);


--
-- Name: ix_schedule_optimization_logs_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_schedule_optimization_logs_student_id ON public.schedule_optimization_logs USING btree (student_id);


--
-- Name: ix_student_achievements_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_achievements_student_id ON public.student_achievements USING btree (student_id);


--
-- Name: ix_student_activity_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_events_created_at ON public.student_activity_events USING btree (created_at);


--
-- Name: ix_student_activity_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_events_event_type ON public.student_activity_events USING btree (event_type);


--
-- Name: ix_student_activity_events_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_events_student_id ON public.student_activity_events USING btree (student_id);


--
-- Name: ix_student_activity_sessions_auth_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_sessions_auth_session_id ON public.student_activity_sessions USING btree (auth_session_id);


--
-- Name: ix_student_activity_sessions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_sessions_created_at ON public.student_activity_sessions USING btree (created_at);


--
-- Name: ix_student_activity_sessions_login_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_sessions_login_at ON public.student_activity_sessions USING btree (login_at);


--
-- Name: ix_student_activity_sessions_logout_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_sessions_logout_at ON public.student_activity_sessions USING btree (logout_at);


--
-- Name: ix_student_activity_sessions_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_activity_sessions_student_id ON public.student_activity_sessions USING btree (student_id);


--
-- Name: ix_student_attendance_records_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_attendance_records_date ON public.student_attendance_records USING btree (date);


--
-- Name: ix_student_attendance_records_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_attendance_records_status ON public.student_attendance_records USING btree (status);


--
-- Name: ix_student_attendance_records_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_attendance_records_student_id ON public.student_attendance_records USING btree (student_id);


--
-- Name: ix_student_course_access_course_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_course_access_course_id ON public.student_course_access USING btree (course_id);


--
-- Name: ix_student_course_access_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_course_access_expires_at ON public.student_course_access USING btree (expires_at);


--
-- Name: ix_student_course_access_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_course_access_student_id ON public.student_course_access USING btree (student_id);


--
-- Name: ix_student_engagement_events_activity_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_engagement_events_activity_session_id ON public.student_engagement_events USING btree (activity_session_id);


--
-- Name: ix_student_engagement_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_engagement_events_event_type ON public.student_engagement_events USING btree (event_type);


--
-- Name: ix_student_engagement_events_occurred_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_engagement_events_occurred_at ON public.student_engagement_events USING btree (occurred_at);


--
-- Name: ix_student_engagement_events_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_engagement_events_student_id ON public.student_engagement_events USING btree (student_id);


--
-- Name: ix_student_grade_reports_course_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_grade_reports_course_id ON public.student_grade_reports USING btree (course_id);


--
-- Name: ix_student_grade_reports_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_grade_reports_student_id ON public.student_grade_reports USING btree (student_id);


--
-- Name: ix_student_learning_profiles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_learning_profiles_user_id ON public.student_learning_profiles USING btree (user_id);


--
-- Name: ix_student_lesson_progress_lesson_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_lesson_progress_lesson_id ON public.student_lesson_progress USING btree (lesson_id);


--
-- Name: ix_student_lesson_progress_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_lesson_progress_started_at ON public.student_lesson_progress USING btree (started_at);


--
-- Name: ix_student_lesson_progress_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_lesson_progress_student_id ON public.student_lesson_progress USING btree (student_id);


--
-- Name: ix_student_parent_note_reads_note_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_note_reads_note_id ON public.student_parent_note_reads USING btree (note_id);


--
-- Name: ix_student_parent_note_reads_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_note_reads_parent_id ON public.student_parent_note_reads USING btree (parent_id);


--
-- Name: ix_student_parent_note_replies_author_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_note_replies_author_id ON public.student_parent_note_replies USING btree (author_id);


--
-- Name: ix_student_parent_note_replies_note_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_note_replies_note_id ON public.student_parent_note_replies USING btree (note_id);


--
-- Name: ix_student_parent_notes_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_notes_category ON public.student_parent_notes USING btree (category);


--
-- Name: ix_student_parent_notes_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_notes_priority ON public.student_parent_notes USING btree (priority);


--
-- Name: ix_student_parent_notes_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_notes_status ON public.student_parent_notes USING btree (status);


--
-- Name: ix_student_parent_notes_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_notes_student_id ON public.student_parent_notes USING btree (student_id);


--
-- Name: ix_student_parent_notes_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_parent_notes_teacher_profile_id ON public.student_parent_notes USING btree (teacher_profile_id);


--
-- Name: ix_student_profiles_last_activity_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_profiles_last_activity_at ON public.student_profiles USING btree (last_activity_at);


--
-- Name: ix_student_profiles_parent_link_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_student_profiles_parent_link_code ON public.student_profiles USING btree (parent_link_code);


--
-- Name: ix_student_routine_profiles_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_routine_profiles_student_id ON public.student_routine_profiles USING btree (student_id);


--
-- Name: ix_student_schedules_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_schedules_student_id ON public.student_schedules USING btree (student_id);


--
-- Name: ix_student_schedules_week_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_schedules_week_start ON public.student_schedules USING btree (week_start);


--
-- Name: ix_student_study_streaks_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_study_streaks_student_id ON public.student_study_streaks USING btree (student_id);


--
-- Name: ix_student_subject_choices_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_subject_choices_student_id ON public.student_subject_choices USING btree (student_id);


--
-- Name: ix_student_subject_choices_subject_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_subject_choices_subject_id ON public.student_subject_choices USING btree (subject_id);


--
-- Name: ix_student_teacher_choices_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_teacher_choices_student_id ON public.student_teacher_choices USING btree (student_id);


--
-- Name: ix_student_teacher_choices_subject_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_teacher_choices_subject_id ON public.student_teacher_choices USING btree (subject_id);


--
-- Name: ix_student_teacher_choices_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_teacher_choices_teacher_profile_id ON public.student_teacher_choices USING btree (teacher_profile_id);


--
-- Name: ix_student_xp_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_student_xp_student_id ON public.student_xp USING btree (student_id);


--
-- Name: ix_study_sessions_schedule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_study_sessions_schedule_id ON public.study_sessions USING btree (schedule_id);


--
-- Name: ix_study_sessions_starts_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_study_sessions_starts_at ON public.study_sessions USING btree (starts_at);


--
-- Name: ix_study_sessions_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_study_sessions_student_id ON public.study_sessions USING btree (student_id);


--
-- Name: ix_subjects_grade; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subjects_grade ON public.subjects USING btree (grade);


--
-- Name: ix_subjects_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_subjects_slug ON public.subjects USING btree (slug);


--
-- Name: ix_teacher_achievements_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_achievements_teacher_profile_id ON public.teacher_achievements USING btree (teacher_profile_id);


--
-- Name: ix_teacher_professional_documents_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_professional_documents_teacher_profile_id ON public.teacher_professional_documents USING btree (teacher_profile_id);


--
-- Name: ix_teacher_profiles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_teacher_profiles_user_id ON public.teacher_profiles USING btree (user_id);


--
-- Name: ix_teacher_qualifications_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_qualifications_teacher_profile_id ON public.teacher_qualifications USING btree (teacher_profile_id);


--
-- Name: ix_teacher_student_notes_student_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_student_notes_student_id ON public.teacher_student_notes USING btree (student_id);


--
-- Name: ix_teacher_student_notes_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_student_notes_teacher_profile_id ON public.teacher_student_notes USING btree (teacher_profile_id);


--
-- Name: ix_teacher_teaching_experiences_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_teaching_experiences_teacher_profile_id ON public.teacher_teaching_experiences USING btree (teacher_profile_id);


--
-- Name: ix_teacher_voice_samples_profile; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_voice_samples_profile ON public.teacher_voice_samples USING btree (teacher_profile_id);


--
-- Name: ix_teacher_why_study_points_teacher_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_teacher_why_study_points_teacher_profile_id ON public.teacher_why_study_points USING btree (teacher_profile_id);


--
-- Name: ix_two_factor_challenges_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_two_factor_challenges_expires_at ON public.two_factor_challenges USING btree (expires_at);


--
-- Name: ix_two_factor_challenges_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_two_factor_challenges_token_hash ON public.two_factor_challenges USING btree (challenge_token_hash);


--
-- Name: ix_two_factor_challenges_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_two_factor_challenges_user_id ON public.two_factor_challenges USING btree (user_id);


--
-- Name: ix_user_roles_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_roles_role_id ON public.user_roles USING btree (role_id);


--
-- Name: ix_user_roles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_roles_user_id ON public.user_roles USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_email_verified_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_email_verified_at ON public.users USING btree (email_verified_at);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_two_factor_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_two_factor_enabled ON public.users USING btree (two_factor_enabled);


--
-- Name: uq_threads_parent_teacher_student_course; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_threads_parent_teacher_student_course ON public.conversation_threads USING btree (parent_user_id, teacher_user_id, student_id, course_id) WHERE ((parent_user_id IS NOT NULL) AND (teacher_user_id IS NOT NULL) AND (course_id IS NOT NULL) AND ((thread_type)::text = 'teacher_parent'::text));


--
-- Name: uq_threads_teacher_student_course; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_threads_teacher_student_course ON public.conversation_threads USING btree (teacher_user_id, student_id, course_id) WHERE ((course_id IS NOT NULL) AND (teacher_user_id IS NOT NULL) AND ((thread_type)::text = 'teacher_student'::text));


--
-- Name: uq_threads_teacher_student_legacy; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_threads_teacher_student_legacy ON public.conversation_threads USING btree (teacher_user_id, student_id) WHERE ((course_id IS NULL) AND (teacher_user_id IS NOT NULL));


--
-- Name: ai_jobs ai_jobs_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_jobs
    ADD CONSTRAINT ai_jobs_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE SET NULL;


--
-- Name: audit_logs audit_logs_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: auth_sessions auth_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: availability_blocks availability_blocks_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.availability_blocks
    ADD CONSTRAINT availability_blocks_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE CASCADE;


--
-- Name: chat_messages chat_messages_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: content_chunks content_chunks_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.content_chunks
    ADD CONSTRAINT content_chunks_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE CASCADE;


--
-- Name: conversation_message_reads conversation_message_reads_message_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message_reads
    ADD CONSTRAINT conversation_message_reads_message_id_fkey FOREIGN KEY (message_id) REFERENCES public.conversation_messages(id) ON DELETE CASCADE;


--
-- Name: conversation_message_reads conversation_message_reads_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_message_reads
    ADD CONSTRAINT conversation_message_reads_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: conversation_messages conversation_messages_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_messages
    ADD CONSTRAINT conversation_messages_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: conversation_messages conversation_messages_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_messages
    ADD CONSTRAINT conversation_messages_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.conversation_threads(id) ON DELETE CASCADE;


--
-- Name: conversation_participants conversation_participants_thread_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT conversation_participants_thread_id_fkey FOREIGN KEY (thread_id) REFERENCES public.conversation_threads(id) ON DELETE CASCADE;


--
-- Name: conversation_participants conversation_participants_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_participants
    ADD CONSTRAINT conversation_participants_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: conversation_threads conversation_threads_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_threads
    ADD CONSTRAINT conversation_threads_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: conversation_threads conversation_threads_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_threads
    ADD CONSTRAINT conversation_threads_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: course_analytics course_analytics_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_analytics
    ADD CONSTRAINT course_analytics_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: course_quiz_answers course_quiz_answers_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_answers
    ADD CONSTRAINT course_quiz_answers_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.course_quiz_attempts(id) ON DELETE CASCADE;


--
-- Name: course_quiz_answers course_quiz_answers_graded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_answers
    ADD CONSTRAINT course_quiz_answers_graded_by_user_id_fkey FOREIGN KEY (graded_by_user_id) REFERENCES public.users(id);


--
-- Name: course_quiz_answers course_quiz_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_answers
    ADD CONSTRAINT course_quiz_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.course_quiz_questions(id) ON DELETE CASCADE;


--
-- Name: course_quiz_attempts course_quiz_attempts_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_attempts
    ADD CONSTRAINT course_quiz_attempts_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.course_quizzes(id) ON DELETE CASCADE;


--
-- Name: course_quiz_attempts course_quiz_attempts_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_attempts
    ADD CONSTRAINT course_quiz_attempts_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: course_quiz_questions course_quiz_questions_quiz_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quiz_questions
    ADD CONSTRAINT course_quiz_questions_quiz_id_fkey FOREIGN KEY (quiz_id) REFERENCES public.course_quizzes(id) ON DELETE CASCADE;


--
-- Name: course_quizzes course_quizzes_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.course_quizzes
    ADD CONSTRAINT course_quizzes_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: courses courses_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id);


--
-- Name: courses courses_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id);


--
-- Name: courses courses_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id);


--
-- Name: email_tokens email_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_tokens
    ADD CONSTRAINT email_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: exams exams_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.exams
    ADD CONSTRAINT exams_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_speaking_conversation_sessions fk_conversation_session_scenario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_sessions
    ADD CONSTRAINT fk_conversation_session_scenario FOREIGN KEY (scenario_id) REFERENCES public.language_conversation_scenarios(id) ON DELETE SET NULL;


--
-- Name: conversation_threads fk_conversation_threads_course_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_threads
    ADD CONSTRAINT fk_conversation_threads_course_id FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE SET NULL;


--
-- Name: conversation_threads fk_conversation_threads_parent_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_threads
    ADD CONSTRAINT fk_conversation_threads_parent_user_id FOREIGN KEY (parent_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: conversation_threads fk_conversation_threads_teacher_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_threads
    ADD CONSTRAINT fk_conversation_threads_teacher_user_id FOREIGN KEY (teacher_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: lesson_assets fk_lesson_assets_media_object; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_assets
    ADD CONSTRAINT fk_lesson_assets_media_object FOREIGN KEY (media_object_id) REFERENCES public.media_objects(id) ON DELETE SET NULL;


--
-- Name: student_parent_notes fk_student_parent_notes_closed_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_notes
    ADD CONSTRAINT fk_student_parent_notes_closed_by FOREIGN KEY (closed_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: language_activity_log language_activity_log_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_activity_log
    ADD CONSTRAINT language_activity_log_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_activity_log language_activity_log_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_activity_log
    ADD CONSTRAINT language_activity_log_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_analytics language_analytics_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_analytics
    ADD CONSTRAINT language_analytics_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_analytics language_analytics_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_analytics
    ADD CONSTRAINT language_analytics_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_assessment_skill_scores language_assessment_skill_scores_assessment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessment_skill_scores
    ADD CONSTRAINT language_assessment_skill_scores_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.language_assessments(id) ON DELETE CASCADE;


--
-- Name: language_assessments language_assessments_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessments
    ADD CONSTRAINT language_assessments_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.language_placement_attempts(id) ON DELETE CASCADE;


--
-- Name: language_assessments language_assessments_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessments
    ADD CONSTRAINT language_assessments_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_assessments language_assessments_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_assessments
    ADD CONSTRAINT language_assessments_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_certificates language_certificates_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_certificates
    ADD CONSTRAINT language_certificates_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_certificates language_certificates_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_certificates
    ADD CONSTRAINT language_certificates_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_component_mastery language_component_mastery_component_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_component_mastery
    ADD CONSTRAINT language_component_mastery_component_id_fkey FOREIGN KEY (component_id) REFERENCES public.language_knowledge_components(id) ON DELETE CASCADE;


--
-- Name: language_component_mastery language_component_mastery_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_component_mastery
    ADD CONSTRAINT language_component_mastery_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_component_mastery language_component_mastery_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_component_mastery
    ADD CONSTRAINT language_component_mastery_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_content_items language_content_items_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_content_items
    ADD CONSTRAINT language_content_items_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_content_items language_content_items_media_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_content_items
    ADD CONSTRAINT language_content_items_media_object_id_fkey FOREIGN KEY (media_object_id) REFERENCES public.media_objects(id) ON DELETE SET NULL;


--
-- Name: language_conversation_scenarios language_conversation_scenarios_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_conversation_scenarios
    ADD CONSTRAINT language_conversation_scenarios_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_curriculum_progress language_curriculum_progress_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_curriculum_progress
    ADD CONSTRAINT language_curriculum_progress_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_curriculum_progress language_curriculum_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_curriculum_progress
    ADD CONSTRAINT language_curriculum_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_error_patterns language_error_patterns_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_error_patterns
    ADD CONSTRAINT language_error_patterns_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_error_patterns language_error_patterns_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_error_patterns
    ADD CONSTRAINT language_error_patterns_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_exam_sessions language_exam_sessions_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_exam_sessions
    ADD CONSTRAINT language_exam_sessions_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_exam_sessions language_exam_sessions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_exam_sessions
    ADD CONSTRAINT language_exam_sessions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_generated_questions language_generated_questions_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_generated_questions
    ADD CONSTRAINT language_generated_questions_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_learning_paths language_learning_paths_assessment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_learning_paths
    ADD CONSTRAINT language_learning_paths_assessment_id_fkey FOREIGN KEY (assessment_id) REFERENCES public.language_assessments(id) ON DELETE SET NULL;


--
-- Name: language_learning_paths language_learning_paths_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_learning_paths
    ADD CONSTRAINT language_learning_paths_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_learning_paths language_learning_paths_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_learning_paths
    ADD CONSTRAINT language_learning_paths_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_lesson_audio_cache language_lesson_audio_cache_content_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_lesson_audio_cache
    ADD CONSTRAINT language_lesson_audio_cache_content_item_id_fkey FOREIGN KEY (content_item_id) REFERENCES public.language_content_items(id) ON DELETE CASCADE;


--
-- Name: language_lesson_audio_cache language_lesson_audio_cache_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_lesson_audio_cache
    ADD CONSTRAINT language_lesson_audio_cache_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: language_listening_progress language_listening_progress_content_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_listening_progress
    ADD CONSTRAINT language_listening_progress_content_item_id_fkey FOREIGN KEY (content_item_id) REFERENCES public.language_content_items(id) ON DELETE CASCADE;


--
-- Name: language_listening_progress language_listening_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_listening_progress
    ADD CONSTRAINT language_listening_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_path_items language_path_items_content_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_path_items
    ADD CONSTRAINT language_path_items_content_item_id_fkey FOREIGN KEY (content_item_id) REFERENCES public.language_content_items(id) ON DELETE SET NULL;


--
-- Name: language_path_items language_path_items_path_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_path_items
    ADD CONSTRAINT language_path_items_path_id_fkey FOREIGN KEY (path_id) REFERENCES public.language_learning_paths(id) ON DELETE CASCADE;


--
-- Name: language_placement_attempts language_placement_attempts_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_attempts
    ADD CONSTRAINT language_placement_attempts_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_placement_attempts language_placement_attempts_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_attempts
    ADD CONSTRAINT language_placement_attempts_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_placement_questions language_placement_questions_section_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_questions
    ADD CONSTRAINT language_placement_questions_section_id_fkey FOREIGN KEY (section_id) REFERENCES public.language_placement_sections(id) ON DELETE CASCADE;


--
-- Name: language_placement_responses language_placement_responses_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_responses
    ADD CONSTRAINT language_placement_responses_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.language_placement_attempts(id) ON DELETE CASCADE;


--
-- Name: language_placement_responses language_placement_responses_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_responses
    ADD CONSTRAINT language_placement_responses_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.language_placement_questions(id) ON DELETE CASCADE;


--
-- Name: language_placement_sections language_placement_sections_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_placement_sections
    ADD CONSTRAINT language_placement_sections_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_progress_snapshots language_progress_snapshots_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_progress_snapshots
    ADD CONSTRAINT language_progress_snapshots_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_progress_snapshots language_progress_snapshots_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_progress_snapshots
    ADD CONSTRAINT language_progress_snapshots_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_pronunciation_scores language_pronunciation_scores_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_pronunciation_scores
    ADD CONSTRAINT language_pronunciation_scores_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_pronunciation_scores language_pronunciation_scores_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_pronunciation_scores
    ADD CONSTRAINT language_pronunciation_scores_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_reading_progress language_reading_progress_content_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_reading_progress
    ADD CONSTRAINT language_reading_progress_content_item_id_fkey FOREIGN KEY (content_item_id) REFERENCES public.language_content_items(id) ON DELETE CASCADE;


--
-- Name: language_reading_progress language_reading_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_reading_progress
    ADD CONSTRAINT language_reading_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_scenario_progress language_scenario_progress_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_scenario_progress
    ADD CONSTRAINT language_scenario_progress_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_scenario_progress language_scenario_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_scenario_progress
    ADD CONSTRAINT language_scenario_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_skill_level_state language_skill_level_state_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_skill_level_state
    ADD CONSTRAINT language_skill_level_state_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_skill_level_state language_skill_level_state_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_skill_level_state
    ADD CONSTRAINT language_skill_level_state_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_speaking_conversation_sessions language_speaking_conversation_sessions_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_sessions
    ADD CONSTRAINT language_speaking_conversation_sessions_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_speaking_conversation_sessions language_speaking_conversation_sessions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_sessions
    ADD CONSTRAINT language_speaking_conversation_sessions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_speaking_conversation_turns language_speaking_conversation_turns_reply_media_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_turns
    ADD CONSTRAINT language_speaking_conversation_turns_reply_media_object_id_fkey FOREIGN KEY (reply_media_object_id) REFERENCES public.media_objects(id) ON DELETE SET NULL;


--
-- Name: language_speaking_conversation_turns language_speaking_conversation_turns_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_turns
    ADD CONSTRAINT language_speaking_conversation_turns_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.language_speaking_conversation_sessions(id) ON DELETE CASCADE;


--
-- Name: language_speaking_conversation_turns language_speaking_conversation_turns_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_turns
    ADD CONSTRAINT language_speaking_conversation_turns_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_speaking_conversation_turns language_speaking_conversation_turns_user_media_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_conversation_turns
    ADD CONSTRAINT language_speaking_conversation_turns_user_media_object_id_fkey FOREIGN KEY (user_media_object_id) REFERENCES public.media_objects(id) ON DELETE SET NULL;


--
-- Name: language_speaking_progress language_speaking_progress_content_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_progress
    ADD CONSTRAINT language_speaking_progress_content_item_id_fkey FOREIGN KEY (content_item_id) REFERENCES public.language_content_items(id) ON DELETE CASCADE;


--
-- Name: language_speaking_progress language_speaking_progress_media_object_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_progress
    ADD CONSTRAINT language_speaking_progress_media_object_id_fkey FOREIGN KEY (media_object_id) REFERENCES public.media_objects(id) ON DELETE CASCADE;


--
-- Name: language_speaking_progress language_speaking_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_speaking_progress
    ADD CONSTRAINT language_speaking_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_streaks language_streaks_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_streaks
    ADD CONSTRAINT language_streaks_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_streaks language_streaks_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_streaks
    ADD CONSTRAINT language_streaks_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_student_achievements language_student_achievements_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_achievements
    ADD CONSTRAINT language_student_achievements_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_student_achievements language_student_achievements_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_achievements
    ADD CONSTRAINT language_student_achievements_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_student_profiles language_student_profiles_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_profiles
    ADD CONSTRAINT language_student_profiles_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_student_profiles language_student_profiles_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_student_profiles
    ADD CONSTRAINT language_student_profiles_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_subscriptions language_subscriptions_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_subscriptions
    ADD CONSTRAINT language_subscriptions_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id) ON DELETE SET NULL;


--
-- Name: language_subscriptions language_subscriptions_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_subscriptions
    ADD CONSTRAINT language_subscriptions_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.language_products(id) ON DELETE CASCADE;


--
-- Name: language_subscriptions language_subscriptions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_subscriptions
    ADD CONSTRAINT language_subscriptions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_vocabulary_catalog_seen language_vocabulary_catalog_seen_catalog_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog_seen
    ADD CONSTRAINT language_vocabulary_catalog_seen_catalog_id_fkey FOREIGN KEY (catalog_id) REFERENCES public.language_vocabulary_catalog(id) ON DELETE CASCADE;


--
-- Name: language_vocabulary_catalog_seen language_vocabulary_catalog_seen_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_catalog_seen
    ADD CONSTRAINT language_vocabulary_catalog_seen_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_vocabulary_progress language_vocabulary_progress_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_progress
    ADD CONSTRAINT language_vocabulary_progress_language_id_fkey FOREIGN KEY (language_id) REFERENCES public.languages(id) ON DELETE CASCADE;


--
-- Name: language_vocabulary_progress language_vocabulary_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_vocabulary_progress
    ADD CONSTRAINT language_vocabulary_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: language_writing_progress language_writing_progress_content_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_writing_progress
    ADD CONSTRAINT language_writing_progress_content_item_id_fkey FOREIGN KEY (content_item_id) REFERENCES public.language_content_items(id) ON DELETE CASCADE;


--
-- Name: language_writing_progress language_writing_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.language_writing_progress
    ADD CONSTRAINT language_writing_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: lesson_assets lesson_assets_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lesson_assets
    ADD CONSTRAINT lesson_assets_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE CASCADE;


--
-- Name: lessons lessons_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lessons
    ADD CONSTRAINT lessons_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.users(id);


--
-- Name: media_objects media_objects_uploaded_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_objects
    ADD CONSTRAINT media_objects_uploaded_by_user_id_fkey FOREIGN KEY (uploaded_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: parent_notification_settings parent_notification_settings_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notification_settings
    ADD CONSTRAINT parent_notification_settings_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: parent_notification_settings parent_notification_settings_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_notification_settings
    ADD CONSTRAINT parent_notification_settings_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: parent_student_links parent_student_links_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student_links
    ADD CONSTRAINT parent_student_links_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: parent_student_links parent_student_links_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parent_student_links
    ADD CONSTRAINT parent_student_links_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payment_items payment_items_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_items
    ADD CONSTRAINT payment_items_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id);


--
-- Name: payment_items payment_items_language_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_items
    ADD CONSTRAINT payment_items_language_product_id_fkey FOREIGN KEY (language_product_id) REFERENCES public.language_products(id) ON DELETE CASCADE;


--
-- Name: payment_items payment_items_payment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_items
    ADD CONSTRAINT payment_items_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.payments(id) ON DELETE CASCADE;


--
-- Name: payments payments_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: planner_chat_messages planner_chat_messages_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_chat_messages
    ADD CONSTRAINT planner_chat_messages_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: planner_life_events planner_life_events_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_life_events
    ADD CONSTRAINT planner_life_events_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: planner_profiles planner_profiles_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_profiles
    ADD CONSTRAINT planner_profiles_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: planner_schedule_slots planner_schedule_slots_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.planner_schedule_slots
    ADD CONSTRAINT planner_schedule_slots_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: quiz_attempts quiz_attempts_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE CASCADE;


--
-- Name: quiz_attempts quiz_attempts_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quiz_attempts
    ADD CONSTRAINT quiz_attempts_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: quiz_questions quiz_questions_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.quiz_questions
    ADD CONSTRAINT quiz_questions_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE CASCADE;


--
-- Name: routine_slots routine_slots_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.routine_slots
    ADD CONSTRAINT routine_slots_profile_id_fkey FOREIGN KEY (profile_id) REFERENCES public.student_routine_profiles(id) ON DELETE CASCADE;


--
-- Name: schedule_optimization_logs schedule_optimization_logs_schedule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_optimization_logs
    ADD CONSTRAINT schedule_optimization_logs_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.student_schedules(id) ON DELETE SET NULL;


--
-- Name: schedule_optimization_logs schedule_optimization_logs_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_optimization_logs
    ADD CONSTRAINT schedule_optimization_logs_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_achievements student_achievements_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_achievements
    ADD CONSTRAINT student_achievements_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_activity_events student_activity_events_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_activity_events
    ADD CONSTRAINT student_activity_events_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: student_activity_sessions student_activity_sessions_auth_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_activity_sessions
    ADD CONSTRAINT student_activity_sessions_auth_session_id_fkey FOREIGN KEY (auth_session_id) REFERENCES public.auth_sessions(id) ON DELETE SET NULL;


--
-- Name: student_activity_sessions student_activity_sessions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_activity_sessions
    ADD CONSTRAINT student_activity_sessions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_analytics student_analytics_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_analytics
    ADD CONSTRAINT student_analytics_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_attendance_records student_attendance_records_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_attendance_records
    ADD CONSTRAINT student_attendance_records_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id);


--
-- Name: student_course_access student_course_access_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_course_access
    ADD CONSTRAINT student_course_access_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: student_course_access student_course_access_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_course_access
    ADD CONSTRAINT student_course_access_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_engagement_events student_engagement_events_activity_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_engagement_events
    ADD CONSTRAINT student_engagement_events_activity_session_id_fkey FOREIGN KEY (activity_session_id) REFERENCES public.student_activity_sessions(id) ON DELETE SET NULL;


--
-- Name: student_engagement_events student_engagement_events_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_engagement_events
    ADD CONSTRAINT student_engagement_events_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_grade_reports student_grade_reports_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_grade_reports
    ADD CONSTRAINT student_grade_reports_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- Name: student_grade_reports student_grade_reports_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_grade_reports
    ADD CONSTRAINT student_grade_reports_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_learning_profiles student_learning_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_learning_profiles
    ADD CONSTRAINT student_learning_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_lesson_progress student_lesson_progress_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_lesson_progress
    ADD CONSTRAINT student_lesson_progress_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE CASCADE;


--
-- Name: student_lesson_progress student_lesson_progress_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_lesson_progress
    ADD CONSTRAINT student_lesson_progress_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_parent_note_reads student_parent_note_reads_note_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_reads
    ADD CONSTRAINT student_parent_note_reads_note_id_fkey FOREIGN KEY (note_id) REFERENCES public.student_parent_notes(id) ON DELETE CASCADE;


--
-- Name: student_parent_note_reads student_parent_note_reads_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_reads
    ADD CONSTRAINT student_parent_note_reads_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_parent_note_replies student_parent_note_replies_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_replies
    ADD CONSTRAINT student_parent_note_replies_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_parent_note_replies student_parent_note_replies_note_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_note_replies
    ADD CONSTRAINT student_parent_note_replies_note_id_fkey FOREIGN KEY (note_id) REFERENCES public.student_parent_notes(id) ON DELETE CASCADE;


--
-- Name: student_parent_notes student_parent_notes_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_notes
    ADD CONSTRAINT student_parent_notes_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_parent_notes student_parent_notes_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_parent_notes
    ADD CONSTRAINT student_parent_notes_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: student_profiles student_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_profiles
    ADD CONSTRAINT student_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: student_routine_profiles student_routine_profiles_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_routine_profiles
    ADD CONSTRAINT student_routine_profiles_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_schedules student_schedules_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_schedules
    ADD CONSTRAINT student_schedules_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_study_streaks student_study_streaks_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_study_streaks
    ADD CONSTRAINT student_study_streaks_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_subject_choices student_subject_choices_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_subject_choices
    ADD CONSTRAINT student_subject_choices_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_subject_choices student_subject_choices_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_subject_choices
    ADD CONSTRAINT student_subject_choices_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: student_teacher_choices student_teacher_choices_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_teacher_choices
    ADD CONSTRAINT student_teacher_choices_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: student_teacher_choices student_teacher_choices_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_teacher_choices
    ADD CONSTRAINT student_teacher_choices_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: student_teacher_choices student_teacher_choices_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_teacher_choices
    ADD CONSTRAINT student_teacher_choices_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id);


--
-- Name: student_xp student_xp_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.student_xp
    ADD CONSTRAINT student_xp_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: study_sessions study_sessions_lesson_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions
    ADD CONSTRAINT study_sessions_lesson_id_fkey FOREIGN KEY (lesson_id) REFERENCES public.lessons(id) ON DELETE SET NULL;


--
-- Name: study_sessions study_sessions_schedule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions
    ADD CONSTRAINT study_sessions_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.student_schedules(id) ON DELETE CASCADE;


--
-- Name: study_sessions study_sessions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.study_sessions
    ADD CONSTRAINT study_sessions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: teacher_achievements teacher_achievements_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_achievements
    ADD CONSTRAINT teacher_achievements_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_analytics teacher_analytics_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_analytics
    ADD CONSTRAINT teacher_analytics_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_professional_documents teacher_professional_documents_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_professional_documents
    ADD CONSTRAINT teacher_professional_documents_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_profile_grades teacher_profile_grades_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_grades
    ADD CONSTRAINT teacher_profile_grades_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_profile_subjects teacher_profile_subjects_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_subjects
    ADD CONSTRAINT teacher_profile_subjects_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE;


--
-- Name: teacher_profile_subjects teacher_profile_subjects_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profile_subjects
    ADD CONSTRAINT teacher_profile_subjects_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_profiles teacher_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_profiles
    ADD CONSTRAINT teacher_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: teacher_qualifications teacher_qualifications_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_qualifications
    ADD CONSTRAINT teacher_qualifications_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_student_notes teacher_student_notes_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_student_notes
    ADD CONSTRAINT teacher_student_notes_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: teacher_student_notes teacher_student_notes_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_student_notes
    ADD CONSTRAINT teacher_student_notes_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_teaching_experiences teacher_teaching_experiences_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_teaching_experiences
    ADD CONSTRAINT teacher_teaching_experiences_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_voice_samples teacher_voice_samples_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_voice_samples
    ADD CONSTRAINT teacher_voice_samples_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: teacher_why_study_points teacher_why_study_points_teacher_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teacher_why_study_points
    ADD CONSTRAINT teacher_why_study_points_teacher_profile_id_fkey FOREIGN KEY (teacher_profile_id) REFERENCES public.teacher_profiles(id) ON DELETE CASCADE;


--
-- Name: two_factor_challenges two_factor_challenges_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.two_factor_challenges
    ADD CONSTRAINT two_factor_challenges_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE CASCADE;


--
-- Name: user_roles user_roles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_roles
    ADD CONSTRAINT user_roles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--
