package com.rork.eduspark.di

import com.rork.eduspark.BuildConfig
import com.rork.eduspark.core.connectivity.ConnectivityObserver
import com.rork.eduspark.core.locale.LocaleController
import com.rork.eduspark.core.network.createEduMindHttpClient
import com.rork.eduspark.core.preferences.AppPreferences
import com.rork.eduspark.core.session.EncryptedTokenStore
import com.rork.eduspark.core.session.InMemoryTokenStore
import com.rork.eduspark.core.session.SecureTokenStore
import com.rork.eduspark.data.local.ParentReportExportStore
import com.rork.eduspark.data.model.UserRole
import com.rork.eduspark.data.repository.AchievementRepository
import com.rork.eduspark.data.repository.AuthRepository
import com.rork.eduspark.data.repository.CertificateRepository
import com.rork.eduspark.data.repository.LearningRepository
import com.rork.eduspark.data.repository.LanguageRepository
import com.rork.eduspark.data.repository.MessagingRepository
import com.rork.eduspark.data.repository.NotificationRepository
import com.rork.eduspark.data.repository.ExamRepository
import com.rork.eduspark.data.repository.OnboardingRepository
import com.rork.eduspark.data.repository.ParentRepository
import com.rork.eduspark.data.repository.PaymentRepository
import com.rork.eduspark.data.repository.PlannerRepository
import com.rork.eduspark.data.repository.ProfileRepository
import com.rork.eduspark.data.repository.ProjectRepository
import com.rork.eduspark.data.repository.QuizRepository
import com.rork.eduspark.data.repository.RoutineRepository
import com.rork.eduspark.data.repository.SecurityRepository
import com.rork.eduspark.data.repository.SubscriptionRepository
import com.rork.eduspark.data.repository.TeacherRepository
import com.rork.eduspark.data.repository.TeacherLessonUploadRepository
import com.rork.eduspark.data.repository.TeacherSetupRepository
import com.rork.eduspark.data.repository.TutorRepository
import com.rork.eduspark.data.repository.VoucherRepository
import com.rork.eduspark.data.repository.mock.MockAchievementRepository
import com.rork.eduspark.data.repository.mock.MockAuthRepository
import com.rork.eduspark.data.repository.mock.MockCertificateRepository
import com.rork.eduspark.data.repository.mock.MockExamRepository
import com.rork.eduspark.data.repository.mock.MockLearningRepository
import com.rork.eduspark.data.repository.mock.MockLanguageRepository
import com.rork.eduspark.data.repository.mock.MockMessagingRepository
import com.rork.eduspark.data.repository.mock.MockNotificationRepository
import com.rork.eduspark.data.repository.mock.MockOnboardingRepository
import com.rork.eduspark.data.repository.mock.MockPaymentRepository
import com.rork.eduspark.data.repository.mock.MockPlannerRepository
import com.rork.eduspark.data.repository.mock.MockProfileRepository
import com.rork.eduspark.data.repository.mock.MockProjectRepository
import com.rork.eduspark.data.repository.mock.MockQuizRepository
import com.rork.eduspark.data.repository.mock.MockRoutineRepository
import com.rork.eduspark.data.repository.mock.MockSecurityRepository
import com.rork.eduspark.data.repository.mock.MockStudentEntitlements
import com.rork.eduspark.data.repository.mock.MockSubscriptionRepository
import com.rork.eduspark.data.repository.mock.MockTeacherRepository
import com.rork.eduspark.data.repository.mock.MockTeacherLessonUploadRepository
import com.rork.eduspark.data.repository.mock.MockTutorRepository
import com.rork.eduspark.data.repository.mock.MockVoucherRepository
import com.rork.eduspark.data.remote.auth.AuthApi
import com.rork.eduspark.data.remote.auth.KtorAuthApi
import com.rork.eduspark.data.remote.gamification.KtorStudentGamificationApi
import com.rork.eduspark.data.remote.gamification.StudentGamificationApi
import com.rork.eduspark.data.remote.onboarding.KtorStudentOnboardingApi
import com.rork.eduspark.data.remote.onboarding.StudentOnboardingApi
import com.rork.eduspark.data.remote.parent.KtorParentApi
import com.rork.eduspark.data.remote.parent.ParentApi
import com.rork.eduspark.data.remote.learning.KtorStudentLearningApi
import com.rork.eduspark.data.remote.learning.StudentLearningApi
import com.rork.eduspark.data.remote.planner.KtorStudentPlannerApi
import com.rork.eduspark.data.remote.planner.StudentPlannerApi
import com.rork.eduspark.data.remote.profile.KtorStudentProfileApi
import com.rork.eduspark.data.remote.profile.StudentProfileApi
import com.rork.eduspark.data.remote.routine.KtorStudentRoutineApi
import com.rork.eduspark.data.remote.routine.StudentRoutineApi
import com.rork.eduspark.data.remote.teacher.KtorTeacherParentNotesApi
import com.rork.eduspark.data.remote.teacher.KtorTeacherCoursesApi
import com.rork.eduspark.data.remote.teacher.KtorTeacherLessonUploadApi
import com.rork.eduspark.data.remote.teacher.KtorTeacherSetupApi
import com.rork.eduspark.data.remote.teacher.TeacherParentNotesApi
import com.rork.eduspark.data.remote.teacher.TeacherCoursesApi
import com.rork.eduspark.data.remote.teacher.TeacherLessonUploadApi
import com.rork.eduspark.data.remote.teacher.TeacherSetupApi
import com.rork.eduspark.data.remote.media.KtorMediaApi
import com.rork.eduspark.data.remote.media.MediaApi
import com.rork.eduspark.data.remote.media.MediaUrlResolver
import com.rork.eduspark.data.remote.messaging.KtorMessagingApi
import com.rork.eduspark.data.remote.messaging.MessagingApi
import com.rork.eduspark.data.remote.quiz.CourseQuizApi
import com.rork.eduspark.data.remote.quiz.KtorCourseQuizApi
import com.rork.eduspark.data.remote.quiz.KtorLessonQuizApi
import com.rork.eduspark.data.remote.quiz.LessonQuizApi
import com.rork.eduspark.data.repository.remote.AuthRefreshCoordinator
import com.rork.eduspark.data.repository.remote.RemoteAchievementRepository
import com.rork.eduspark.data.repository.remote.RemoteAuthRepository
import com.rork.eduspark.data.repository.remote.RemoteLearningRepository
import com.rork.eduspark.data.repository.remote.RemoteMessagingRepository
import com.rork.eduspark.data.repository.remote.RemoteParentRepository
import com.rork.eduspark.data.repository.remote.RemotePlannerRepository
import com.rork.eduspark.data.repository.remote.RemotePaymentRepository
import com.rork.eduspark.data.repository.remote.RemoteProfileRepository
import com.rork.eduspark.data.repository.remote.RemoteQuizRepository
import com.rork.eduspark.data.repository.remote.RemoteRoutineRepository
import com.rork.eduspark.data.repository.remote.RemoteStudentOnboardingRepository
import com.rork.eduspark.data.repository.remote.RemoteSubscriptionRepository
import com.rork.eduspark.data.repository.remote.UnavailableVoucherRepository
import com.rork.eduspark.data.repository.remote.RemoteTeacherSetupRepository
import com.rork.eduspark.data.repository.remote.RemoteTeacherLessonUploadRepository
import com.rork.eduspark.data.repository.remote.TeacherRepositoryWithRemoteCourses
import com.rork.eduspark.data.repository.remote.TeacherRepositoryWithRemoteParentNotes
import com.rork.eduspark.data.repository.remote.TeacherRepositoryWithRemoteQuizzes
import com.rork.eduspark.ui.AppShellViewModel
import com.rork.eduspark.ui.navigation.StudentNavigationDrawerViewModel
import com.rork.eduspark.ui.screens.auth.CertificateVerifyViewModel
import com.rork.eduspark.ui.screens.auth.ForgotPasswordViewModel
import com.rork.eduspark.ui.screens.auth.LoginViewModel
import com.rork.eduspark.ui.screens.auth.RegisterViewModel
import com.rork.eduspark.ui.screens.auth.ResetPasswordViewModel
import com.rork.eduspark.ui.screens.auth.SplashViewModel
import com.rork.eduspark.ui.screens.auth.TwoFactorViewModel
import com.rork.eduspark.ui.screens.auth.ValueCarouselViewModel
import com.rork.eduspark.ui.screens.auth.VerifyEmailViewModel
import com.rork.eduspark.ui.screens.onboarding.OnboardingViewModel
import com.rork.eduspark.ui.screens.parent.ParentDashboardViewModel
import com.rork.eduspark.ui.screens.parent.ParentAiInsightsViewModel
import com.rork.eduspark.ui.screens.parent.ParentAlertsViewModel
import com.rork.eduspark.ui.screens.parent.ParentAttendanceStudyTimeViewModel
import com.rork.eduspark.ui.screens.parent.ParentHomeViewModel
import com.rork.eduspark.ui.screens.parent.ParentLessonDetailsViewModel
import com.rork.eduspark.ui.screens.parent.ParentLessonProgressViewModel
import com.rork.eduspark.ui.screens.parent.ParentLinkStudentViewModel
import com.rork.eduspark.ui.screens.parent.ParentMeViewModel
import com.rork.eduspark.ui.screens.parent.ParentPlannerViewModel
import com.rork.eduspark.ui.screens.parent.ParentProgressViewModel
import com.rork.eduspark.ui.screens.parent.ParentReportsViewModel
import com.rork.eduspark.ui.screens.parent.ParentSubjectsTeachersViewModel
import com.rork.eduspark.ui.screens.student.CourseDetailViewModel
import com.rork.eduspark.ui.screens.student.ExamCaptureViewModel
import com.rork.eduspark.ui.screens.student.LessonPlayerViewModel
import com.rork.eduspark.ui.screens.student.LanguageModuleViewModel
import com.rork.eduspark.ui.screens.student.NotificationSettingsViewModel
import com.rork.eduspark.ui.screens.student.PaymentMethodViewModel
import com.rork.eduspark.ui.screens.student.ParentLinkingViewModel
import com.rork.eduspark.ui.screens.student.PaymentPendingViewModel
import com.rork.eduspark.ui.screens.student.PaywallViewModel
import com.rork.eduspark.ui.screens.student.AccountSettingsViewModel
import com.rork.eduspark.ui.screens.student.PlannerChatViewModel
import com.rork.eduspark.ui.screens.student.PlannerViewModel
import com.rork.eduspark.ui.screens.student.MaterialsSafetyViewModel
import com.rork.eduspark.ui.screens.student.PeerReviewViewModel
import com.rork.eduspark.ui.screens.student.PortfolioViewModel
import com.rork.eduspark.ui.screens.student.ProjectCertificateViewModel
import com.rork.eduspark.ui.screens.student.ProjectDetailViewModel
import com.rork.eduspark.ui.screens.student.ProjectShowcaseDetailViewModel
import com.rork.eduspark.ui.screens.student.ProjectsHubViewModel
import com.rork.eduspark.ui.screens.student.MilestoneBoardViewModel
import com.rork.eduspark.ui.screens.student.ProjectReviewViewModel
import com.rork.eduspark.ui.screens.student.PurchaseSuccessViewModel
import com.rork.eduspark.ui.screens.student.ReflectionLogViewModel
import com.rork.eduspark.ui.screens.student.QuizResultsViewModel
import com.rork.eduspark.ui.screens.student.QuizRunnerViewModel
import com.rork.eduspark.ui.screens.student.AchievementViewModel
import com.rork.eduspark.ui.screens.student.RoutineBuilderViewModel
import com.rork.eduspark.ui.screens.student.RoutineViewModel
import com.rork.eduspark.ui.screens.student.SecuritySettingsViewModel
import com.rork.eduspark.ui.screens.student.LearningPreferencesViewModel
import com.rork.eduspark.ui.screens.student.StudentCoursesViewModel
import com.rork.eduspark.ui.screens.student.StudentHomeViewModel
import com.rork.eduspark.ui.screens.student.StudentProfileViewModel
import com.rork.eduspark.ui.screens.student.SubmissionComposerViewModel
import com.rork.eduspark.ui.screens.student.TaskDetailViewModel
import com.rork.eduspark.ui.screens.student.SubscriptionViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherAccountViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherAnalyticsViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherCourseDetailViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherCoursesViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherDashboardViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherGradebookViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherLessonEditorViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherLessonPreviewViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherLessonProcessingViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherLessonUploadViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherProfileViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherProjectEditorViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherProjectsViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherEssayGradeViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherQuizEditorViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherQuizListViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherQuizResultsViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherReviewDetailViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherReviewQueueViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherSetupViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherStudentProfileViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherStudentsViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherParentNoteViewModel
import com.rork.eduspark.ui.screens.teacher.TeacherVoiceProfileViewModel
import com.rork.eduspark.ui.screens.messaging.ConversationThreadViewModel
import com.rork.eduspark.ui.screens.messaging.MessagesBadgeViewModel
import com.rork.eduspark.ui.screens.messaging.MessagesListViewModel
import com.rork.eduspark.ui.screens.messaging.NewConversationViewModel
import com.rork.eduspark.ui.screens.messaging.NotificationsPanelViewModel
import com.rork.eduspark.ui.screens.messaging.TeacherContactViewModel
import com.rork.eduspark.ui.screens.student.TeamWorkspaceViewModel
import com.rork.eduspark.ui.screens.student.TutorChatViewModel
import com.rork.eduspark.ui.screens.student.VoucherRedeemViewModel
import org.koin.android.ext.koin.androidApplication
import org.koin.core.module.dsl.viewModel
import org.koin.dsl.module

/**
 * Dependency graph.
 *
 * The single decision point for mock-vs-real data is [dataSourceMode], read from
 * `BuildConfig.DATA_SOURCE_MODE`. Screens and ViewModels depend only on the repository
 * interfaces, so switching the whole app to the real backend is one constant plus the
 * remote implementations — not a refactor.
 */
enum class DataSourceMode { MOCK, REMOTE }

val dataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.MOCK)

val authDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.AUTH_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val learningDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.LEARNING_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val profileDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.PROFILE_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val plannerDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.PLANNER_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val routineDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.ROUTINE_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val achievementDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.ACHIEVEMENT_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val teacherNotesDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.TEACHER_NOTES_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val quizDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.QUIZ_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val teacherUploadDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.TEACHER_UPLOAD_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val messagingDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.MESSAGING_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val subscriptionDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.SUBSCRIPTION_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

val paymentDataSourceMode: DataSourceMode =
    runCatching { DataSourceMode.valueOf(BuildConfig.PAYMENT_DATA_SOURCE_MODE.uppercase()) }
        .getOrDefault(DataSourceMode.REMOTE)

/**
 * ST-17/ST-18/ST-19 — the only mode this build supports. No Stripe/PayPal/Apple Pay/Google Pay
 * case exists on purpose; adding one is a product decision, not a matter of extending this enum.
 */
enum class PaymentMode { DIRECT }

val paymentMode: PaymentMode = PaymentMode.DIRECT

val appModule = module {

    single { AppPreferences(androidApplication()) }
    single { ConnectivityObserver(androidApplication()) }
    single { LocaleController(androidApplication()) }
    single { ParentReportExportStore(androidApplication()) }
    single { MockStudentEntitlements() }

    single<SecureTokenStore> {
        when (authDataSourceMode) {
            DataSourceMode.MOCK -> InMemoryTokenStore()
            DataSourceMode.REMOTE -> EncryptedTokenStore(androidApplication())
        }
    }
    single { createEduMindHttpClient() }
    single<AuthApi> { KtorAuthApi(client = get(), baseUrl = BuildConfig.API_BASE_URL) }
    single<StudentOnboardingApi> {
        KtorStudentOnboardingApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<ParentApi> {
        KtorParentApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<StudentLearningApi> {
        KtorStudentLearningApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<StudentGamificationApi> {
        KtorStudentGamificationApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<StudentProfileApi> {
        KtorStudentProfileApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<StudentPlannerApi> {
        KtorStudentPlannerApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<StudentRoutineApi> {
        KtorStudentRoutineApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<TeacherSetupApi> {
        KtorTeacherSetupApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<TeacherParentNotesApi> {
        KtorTeacherParentNotesApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<TeacherLessonUploadApi> {
        KtorTeacherLessonUploadApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<TeacherCoursesApi> {
        KtorTeacherCoursesApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<CourseQuizApi> {
        KtorCourseQuizApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }

    single<LessonQuizApi> {
        KtorLessonQuizApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<MediaApi> {
        KtorMediaApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single<MessagingApi> {
        KtorMessagingApi(client = get(), baseUrl = BuildConfig.API_BASE_URL)
    }
    single { AuthRefreshCoordinator(api = get(), tokenStore = get()) }
    single {
        MediaUrlResolver(
            api = get(),
            tokenStore = get(),
            refreshCoordinator = get(),
            authRepository = get(),
            apiBaseUrl = BuildConfig.API_BASE_URL,
        )
    }

    single<AuthRepository> {
        when (authDataSourceMode) {
            DataSourceMode.MOCK -> MockAuthRepository(tokenStore = get())
            DataSourceMode.REMOTE -> RemoteAuthRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                deviceName = android.os.Build.MODEL,
            )
        }
    }

    single<LearningRepository> {
        when (learningDataSourceMode) {
            DataSourceMode.MOCK -> MockLearningRepository(entitlements = get())
            DataSourceMode.REMOTE -> RemoteLearningRepository(
                api = get(),
                gamificationApi = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<LanguageRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockLanguageRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
    }

    single<CertificateRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockCertificateRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
    }

    single<OnboardingRepository> {
        when (authDataSourceMode) {
            DataSourceMode.MOCK -> MockOnboardingRepository()
            DataSourceMode.REMOTE -> RemoteStudentOnboardingRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<ParentRepository> {
        RemoteParentRepository(
            api = get(),
            tokenStore = get(),
            refreshCoordinator = get(),
            authRepository = get(),
        )
    }

    single<TutorRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockTutorRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
    }

    single<QuizRepository> {
        when (quizDataSourceMode) {
            DataSourceMode.MOCK -> MockQuizRepository()
            DataSourceMode.REMOTE -> RemoteQuizRepository(
                api = get(),
                lessonQuizApi = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<PlannerRepository> {
        when (plannerDataSourceMode) {
            DataSourceMode.MOCK -> MockPlannerRepository()
            DataSourceMode.REMOTE -> RemotePlannerRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<RoutineRepository> {
        when (routineDataSourceMode) {
            DataSourceMode.MOCK -> MockRoutineRepository()
            DataSourceMode.REMOTE -> RemoteRoutineRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<ExamRepository> {
        when (plannerDataSourceMode) {
            DataSourceMode.MOCK -> MockExamRepository()
            DataSourceMode.REMOTE -> get<PlannerRepository>() as RemotePlannerRepository
        }
    }

    single<AchievementRepository> {
        when (achievementDataSourceMode) {
            DataSourceMode.MOCK -> MockAchievementRepository()
            DataSourceMode.REMOTE -> RemoteAchievementRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<SubscriptionRepository> {
        when (subscriptionDataSourceMode) {
            DataSourceMode.MOCK -> MockSubscriptionRepository(entitlements = get())
            DataSourceMode.REMOTE -> RemoteSubscriptionRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<PaymentRepository> {
        when (paymentDataSourceMode) {
            DataSourceMode.MOCK -> MockPaymentRepository(entitlements = get())
            DataSourceMode.REMOTE -> RemotePaymentRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<VoucherRepository> {
        val remoteCommerce = paymentDataSourceMode == DataSourceMode.REMOTE ||
            subscriptionDataSourceMode == DataSourceMode.REMOTE
        if (remoteCommerce) {
            UnavailableVoucherRepository()
        } else {
            MockVoucherRepository()
        }
    }

    single<ProfileRepository> {
        when (profileDataSourceMode) {
            DataSourceMode.MOCK -> MockProfileRepository()
            DataSourceMode.REMOTE -> RemoteProfileRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<SecurityRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockSecurityRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
    }

    single<ProjectRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockProjectRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
    }

    single<TeacherRepository> {
        val mockTeacher = when (dataSourceMode) {
            DataSourceMode.MOCK -> MockTeacherRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
        val withCourses = when (teacherUploadDataSourceMode) {
            DataSourceMode.MOCK -> mockTeacher
            DataSourceMode.REMOTE -> TeacherRepositoryWithRemoteCourses(
                delegate = mockTeacher,
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
        val withNotes = when (teacherNotesDataSourceMode) {
            DataSourceMode.MOCK -> withCourses
            DataSourceMode.REMOTE -> TeacherRepositoryWithRemoteParentNotes(
                delegate = withCourses,
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
        when (quizDataSourceMode) {
            DataSourceMode.MOCK -> withNotes
            DataSourceMode.REMOTE -> TeacherRepositoryWithRemoteQuizzes(
                delegate = withNotes,
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }
    single<TeacherLessonUploadRepository> {
        when (teacherUploadDataSourceMode) {
            DataSourceMode.MOCK -> MockTeacherLessonUploadRepository(teacherRepository = get())
            DataSourceMode.REMOTE -> RemoteTeacherLessonUploadRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }
    single<TeacherSetupRepository> {
        when (authDataSourceMode) {
            DataSourceMode.MOCK -> get<TeacherRepository>()
            DataSourceMode.REMOTE -> RemoteTeacherSetupRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
                apiBaseUrl = BuildConfig.API_BASE_URL,
            )
        }
    }

    // Phase 6 · X-01/X-02/X-03 — one canonical thread store shared by Student and Teacher.
    single<MessagingRepository> {
        when (messagingDataSourceMode) {
            DataSourceMode.MOCK -> MockMessagingRepository()
            DataSourceMode.REMOTE -> RemoteMessagingRepository(
                api = get(),
                tokenStore = get(),
                refreshCoordinator = get(),
                authRepository = get(),
            )
        }
    }

    single<NotificationRepository> {
        when (dataSourceMode) {
            DataSourceMode.MOCK -> MockNotificationRepository()
            DataSourceMode.REMOTE -> error(
                "Remote repositories are not implemented yet — see data/repository/remote."
            )
        }
    }

    viewModel { AppShellViewModel(preferences = get(), connectivity = get(), localeController = get()) }
    viewModel { StudentNavigationDrawerViewModel(authRepository = get(), teacherRepository = get()) }
    viewModel { ParentDashboardViewModel(authRepository = get(), parentRepository = get(), connectivity = get()) }
    viewModel { ParentHomeViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { ParentProgressViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { ParentReportsViewModel(parentRepository = get(), connectivity = get(), exportStore = get()) }
    viewModel {
        ParentMeViewModel(
            authRepository = get(),
            parentRepository = get(),
            securityRepository = get(),
            connectivity = get(),
        )
    }
    viewModel { ParentLinkStudentViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { ParentPlannerViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { ParentAlertsViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { ParentAiInsightsViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { ParentAttendanceStudyTimeViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { ParentLessonProgressViewModel(parentRepository = get(), connectivity = get()) }
    viewModel { (lessonId: String) ->
        ParentLessonDetailsViewModel(lessonId = lessonId, parentRepository = get(), connectivity = get())
    }
    viewModel {
        ParentSubjectsTeachersViewModel(
            authRepository = get(),
            parentRepository = get(),
            connectivity = get(),
        )
    }

    // ── Phase 0 · A-01 → A-04, the entry funnel ──────────────────────────
    viewModel {
        SplashViewModel(
            preferences = get(),
            localeController = get(),
            authRepository = get(),
        )
    }
    viewModel { ValueCarouselViewModel(preferences = get()) }
    viewModel { (expectedRole: UserRole) ->
        LoginViewModel(authRepository = get(), connectivity = get(), expectedRole = expectedRole)
    }

    // A-05 / A-06 / A-07 share one ViewModel; the role comes from the destination, so each
    // register route gets its own instance rather than three duplicated definitions.
    viewModel { (role: UserRole) ->
        RegisterViewModel(
            role = role,
            authRepository = get(),
            preferences = get(),
            connectivity = get(),
        )
    }

    // A-08 / A-09 — both parameterised by the email the previous screen was working with.
    viewModel { (email: String) ->
        VerifyEmailViewModel(email = email, authRepository = get(), connectivity = get())
    }
    viewModel { (email: String, expectedRole: UserRole) ->
        TwoFactorViewModel(
            email = email,
            authRepository = get(),
            connectivity = get(),
            expectedRole = expectedRole,
        )
    }

    // A-10 — no parameters; the address is typed on the screen itself.
    viewModel { ForgotPasswordViewModel(authRepository = get(), connectivity = get()) }

    // A-11 — token from the deep link/hand-off, plus whatever email context came with it.
    viewModel { (token: String, email: String) ->
        ResetPasswordViewModel(
            token = token,
            email = email,
            authRepository = get(),
            connectivity = get(),
        )
    }

    // A-12 — public, no AuthRepository dependency by design (see CertificateVerifyViewModel).
    viewModel { (code: String) ->
        CertificateVerifyViewModel(code = code, certificateRepository = get(), connectivity = get())
    }

    // SO-01…SO-05 — one instance shared by every onboarding screen (graph-scoped in
    // AppNavigation via koinViewModel's viewModelStoreOwner), no parameters of its own.
    viewModel {
        OnboardingViewModel(onboardingRepository = get(), authRepository = get(), connectivity = get())
    }

    // ST-01 — no parameters; the session already tells the repository who is asking.
    viewModel {
        StudentHomeViewModel(
            learningRepository = get(),
            achievementRepository = get(),
            plannerRepository = get(),
            routineRepository = get(),
            authRepository = get(),
            connectivity = get(),
        )
    }

    // STUDENT_COURSES tab — course discovery; no parameters, same "session tells the
    // repository who's asking" shape as ST-01.
    viewModel { StudentCoursesViewModel(learningRepository = get(), onboardingRepository = get(), connectivity = get()) }

    // LN-01/LN-04 — one Language module foundation: access gate, placement gate, home,
    // placement exam and the eight peer area hooks all read from the same module repository.
    viewModel { LanguageModuleViewModel(languageRepository = get(), connectivity = get()) }

    // ST-02 — parameterised by which course was tapped on ST-01.
    viewModel { (courseId: String) ->
        CourseDetailViewModel(
            courseId = courseId,
            learningRepository = get(),
            paymentRepository = get(),
            quizRepository = get(),
            connectivity = get(),
        )
    }

    // ST-03 — parameterised by which lesson was tapped on ST-02.
    viewModel { (lessonId: String) ->
        LessonPlayerViewModel(
            lessonId = lessonId,
            learningRepository = get(),
            quizRepository = get(),
            mediaUrlResolver = get(),
            connectivity = get(),
        )
    }

    // ST-04 / ST-05 — one instance shared by both tutor screens (graph-scoped in
    // AppNavigation via koinViewModel's viewModelStoreOwner), parameterised by the lesson
    // they are grounded in.
    viewModel { (lessonId: String, initialPrompt: String?) ->
        TutorChatViewModel(
            lessonId = lessonId,
            initialPrompt = initialPrompt,
            tutorRepository = get(),
            learningRepository = get(),
            connectivity = get(),
        )
    }

    // ST-06 / ST-08 / ST-09 — one shell, parameterised by which quiz was opened; a fresh
    // instance per quiz id (unlike the tutor graph, nothing here needs to be shared across
    // screens — QuizRepository itself is what remembers progress between them).
    viewModel { (quizId: String) ->
        QuizRunnerViewModel(quizId = quizId, quizRepository = get(), connectivity = get())
    }

    // ST-07 — parameterised by which quiz was just submitted (or is being re-viewed).
    viewModel { (quizId: String) ->
        QuizResultsViewModel(quizId = quizId, quizRepository = get(), connectivity = get())
    }

    // ST-10 — no parameters; PlannerRepository's own hot flow is the shared state. Also
    // collects ExamRepository — the minimal ST-14 reflection, not a new planner feature.
    viewModel { PlannerViewModel(plannerRepository = get(), examRepository = get(), learningRepository = get(), routineRepository = get(), connectivity = get()) }

    // ST-11 — no parameters; independent of ST-10's ViewModel by design (see PlannerChatViewModel).
    viewModel { PlannerChatViewModel(plannerRepository = get(), connectivity = get()) }

    // ST-12 — no parameters; a fresh instance per visit, unlike onboarding's graph-scoped
    // ViewModel (see RoutineBuilderViewModel's own doc comment for why that's not needed here).
    viewModel { RoutineBuilderViewModel(routineRepository = get(), connectivity = get()) }

    // ST-13 — no parameters; RoutineRepository's own hot flow is the shared state.
    viewModel { RoutineViewModel(routineRepository = get(), connectivity = get()) }

    // ST-14 — no parameters; ExamRepository's own hot flow is the shared state.
    viewModel { ExamCaptureViewModel(examRepository = get(), connectivity = get()) }

    // ST-15 — reuses LearningRepository for the gamification header (see AchievementViewModel's
    // own doc comment) plus the new AchievementRepository for the badge list.
    viewModel {
        AchievementViewModel(
            achievementRepository = get(),
            learningRepository = get(),
            connectivity = get(),
        )
    }

    // ST-16 — no parameters; read-only, so no hot flow of its own is needed (see
    // SubscriptionRepository's own doc comment for why nothing here can mutate a subscription).
    // PaymentRepository is only for ST-20's "confirmed access" banner — see SubscriptionViewModel's own doc comment.
    viewModel {
        SubscriptionViewModel(
            subscriptionRepository = get(),
            paymentRepository = get(),
            voucherRepository = get(),
            connectivity = get(),
        )
    }

    // ST-17 — parameterised by the course the paywall was opened for.
    viewModel { (courseId: String) ->
        PaywallViewModel(
            courseId = courseId,
            subscriptionRepository = get(),
            paymentRepository = get(),
            voucherRepository = get(),
            connectivity = get(),
        )
    }

    // ST-18 — same courseId ST-17 already resolved an offer for.
    viewModel { (courseId: String) ->
        PaymentMethodViewModel(courseId = courseId, paymentRepository = get(), connectivity = get())
    }

    // ST-19 — courseId + the method chosen on ST-18; PaymentRepository's own hot pendingPayment
    // flow is what makes the record survive navigating away and back (see PaymentRepository's
    // own doc comment — same shared-state shape as PlannerRepository.weekPlan).
    viewModel { (courseId: String, methodId: String) ->
        PaymentPendingViewModel(courseId = courseId, methodId = methodId, paymentRepository = get(), connectivity = get())
    }

    // ST-20 — parameterised by the course the confirmed payment is for.
    viewModel { (courseId: String) ->
        PurchaseSuccessViewModel(
            courseId = courseId,
            paymentRepository = get(),
            subscriptionRepository = get(),
            learningRepository = get(),
            connectivity = get(),
        )
    }

    // ST-21 — no parameters; a fresh instance per visit, same as ST-12's builder.
    viewModel { VoucherRedeemViewModel(voucherRepository = get(), connectivity = get()) }

    // Learning Preferences — new, extends ST-22; ProfileRepository-only, no gamification data.
    viewModel {
        LearningPreferencesViewModel(
            profileRepository = get(),
            connectivity = get(),
        )
    }

    // ST-22 — hosts the STUDENT_ME tab root; reuses LearningRepository for quick stats (level/
    // streak/course progress), same "one gamification source" reasoning as AchievementViewModel.
    viewModel {
        StudentProfileViewModel(
            profileRepository = get(),
            learningRepository = get(),
            authRepository = get(),
            connectivity = get(),
        )
    }

    viewModel { ParentLinkingViewModel(profileRepository = get(), connectivity = get()) }

    // ST-23 — name/avatar edits go through the same ProfileRepository ST-22 uses; email/
    // password/delete-account are all local, ViewModel-owned mock state (see
    // AccountSettingsViewModel's own doc comment for why neither needs a repository).
    viewModel {
        AccountSettingsViewModel(
            profileRepository = get(),
            authRepository = get(),
            connectivity = get(),
        )
    }

    // ST-24 — no parameters; SecurityRepository's own hot flows are the shared state.
    viewModel { SecuritySettingsViewModel(securityRepository = get(), connectivity = get()) }

    // ST-25 has no ViewModel of its own — LanguageDisplayScreen is purely presentational,
    // reading/writing straight through the AppNavigation params AppShellViewModel already
    // supplies (see LanguageDisplayScreen's own doc comment).

    // ST-26 — no parameters; local preferences only, no ConnectivityObserver needed (see
    // NotificationSettingsViewModel's own doc comment).
    viewModel { NotificationSettingsViewModel(preferences = get()) }

    // ── Phase 2 · Projects ─────────────────────────────────────────────────
    // PJ-01 — no parameters; ProjectRepository's own hot activeProjects flow is the shared state.
    viewModel { ProjectsHubViewModel(projectRepository = get(), connectivity = get()) }

    // PJ-02 — parameterised by which catalog project was opened.
    viewModel { (projectId: String) ->
        ProjectDetailViewModel(projectId = projectId, projectRepository = get(), connectivity = get())
    }

    // PJ-03 — parameterised by the (already-started) project id.
    viewModel { (projectId: String) ->
        MilestoneBoardViewModel(projectId = projectId, projectRepository = get(), connectivity = get())
    }

    // PJ-04 — parameterised by project + task id.
    viewModel { (projectId: String, taskId: String) ->
        TaskDetailViewModel(projectId = projectId, taskId = taskId, projectRepository = get(), connectivity = get())
    }

    // PJ-05 — same project + task id PJ-04 already resolved.
    viewModel { (projectId: String, taskId: String) ->
        SubmissionComposerViewModel(projectId = projectId, taskId = taskId, projectRepository = get(), connectivity = get())
    }

    // PJ-06 — same project + task id.
    viewModel { (projectId: String, taskId: String) ->
        ProjectReviewViewModel(projectId = projectId, taskId = taskId, projectRepository = get(), connectivity = get())
    }

    // PJ-07 — no arguments; this slice has exactly one deterministic assignment.
    viewModel { PeerReviewViewModel(projectRepository = get(), connectivity = get()) }

    // PJ-08 — parameterised by project id.
    viewModel { (projectId: String) ->
        TeamWorkspaceViewModel(projectId = projectId, projectRepository = get(), connectivity = get())
    }

    // PJ-09 — parameterised by project + milestone id.
    viewModel { (projectId: String, milestoneId: String) ->
        ReflectionLogViewModel(projectId = projectId, milestoneId = milestoneId, projectRepository = get(), connectivity = get())
    }

    // PJ-10 — no arguments; lists every fully completed project.
    viewModel { PortfolioViewModel(projectRepository = get(), profileRepository = get(), connectivity = get()) }

    // PJ-10 detail — parameterised by project id.
    viewModel { (projectId: String) ->
        ProjectShowcaseDetailViewModel(projectId = projectId, projectRepository = get(), connectivity = get())
    }

    // PJ-11 — parameterised by project id; resolves its code through ProjectRepository, then
    // the record through the same CertificateRepository A-12 already uses.
    viewModel { (projectId: String) ->
        ProjectCertificateViewModel(projectId = projectId, projectRepository = get(), certificateRepository = get(), connectivity = get())
    }

    // PJ-12 — parameterised by project id; only ever opened for a Physical project.
    viewModel { (projectId: String) ->
        MaterialsSafetyViewModel(projectId = projectId, projectRepository = get(), connectivity = get())
    }

    // ── Phase 3 · TC-01 Teacher Setup Wizard / TC-02 Dashboard / TC-03 Courses ──────────
    viewModel { TeacherSetupViewModel(authRepository = get(), teacherSetupRepository = get(), preferences = get(), connectivity = get()) }
    viewModel { TeacherDashboardViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }
    viewModel { TeacherCoursesViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }

    // TC-04 — parameterised by which course was tapped on TC-03.
    viewModel { (courseId: String) ->
        TeacherCourseDetailViewModel(courseId = courseId, authRepository = get(), teacherRepository = get(), connectivity = get())
    }

    // TC-05 — parameterised by the course a lesson is being added to.
    viewModel { (courseId: String) ->
        TeacherLessonUploadViewModel(
            courseId = courseId,
            teacherRepository = get(),
            uploadRepository = get(),
            connectivity = get(),
        )
    }

    // TC-06 — parameterised by which lesson (and its course) is being watched.
    viewModel { (courseId: String, lessonId: String) ->
        TeacherLessonProcessingViewModel(courseId = courseId, lessonId = lessonId, teacherRepository = get(), connectivity = get())
    }

    // TC-07 — parameterised by which lesson is being edited.
    viewModel { (courseId: String, lessonId: String) ->
        TeacherLessonEditorViewModel(courseId = courseId, lessonId = lessonId, teacherRepository = get(), connectivity = get())
    }

    // TC-08 — parameterised by which lesson is being previewed.
    viewModel { (courseId: String, lessonId: String) ->
        TeacherLessonPreviewViewModel(courseId = courseId, lessonId = lessonId, teacherRepository = get(), connectivity = get())
    }

    // TC-09 — no parameters; the session already tells the repository which teacher's profile.
    viewModel { TeacherVoiceProfileViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }

    // TC-10 — no parameters for the list root; the editor is parameterised by which quiz.
    viewModel { TeacherQuizListViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }
    viewModel { (quizId: String) ->
        TeacherQuizEditorViewModel(quizId = quizId, teacherRepository = get(), connectivity = get())
    }

    // TC-11 — parameterised by which quiz's results are being viewed.
    viewModel { (quizId: String) ->
        TeacherQuizResultsViewModel(quizId = quizId, teacherRepository = get(), connectivity = get())
    }
    viewModel { (quizId: String, studentId: String, questionId: String) ->
        TeacherEssayGradeViewModel(
            quizId = quizId,
            studentId = studentId,
            questionId = questionId,
            teacherRepository = get(),
            connectivity = get(),
        )
    }

    // TC-12 — no parameters; the session already tells the repository which teacher's roster.
    viewModel { TeacherStudentsViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }

    // TC-13 — parameterised by which student's profile is being viewed.
    viewModel { (studentId: String) ->
        TeacherStudentProfileViewModel(
            studentId = studentId,
            authRepository = get(),
            teacherRepository = get(),
            messagingRepository = get(),
            connectivity = get(),
        )
    }

    viewModel { (studentId: String) ->
        TeacherParentNoteViewModel(studentId = studentId, teacherRepository = get(), connectivity = get())
    }

    // TC-14 — no parameters; the screen's own course chips select which course's gradebook to show.
    viewModel { TeacherGradebookViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }

    // TC-15 — no parameters; the screen's own course/period filters are held by the ViewModel itself.
    viewModel { TeacherAnalyticsViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }

    // TC-16 — no parameters; the session already tells the repository which teacher's profile. The
    // live-preview screen reuses this exact same ViewModel class (a second Koin-created instance).
    viewModel { TeacherAccountViewModel(authRepository = get(), teacherSetupRepository = get(), connectivity = get()) }
    viewModel {
        TeacherProfileViewModel(
            authRepository = get(),
            teacherSetupRepository = get(),
            mediaUrlResolver = get(),
            connectivity = get(),
        )
    }

    // TC-17 — no parameters for the project list root; the editor is parameterised by which project.
    viewModel { TeacherProjectsViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }
    viewModel { (projectId: String) ->
        TeacherProjectEditorViewModel(projectId = projectId, teacherRepository = get(), connectivity = get())
    }

    // TC-18 — no parameters for the queue root; the detail screen is parameterised by which submission.
    viewModel { TeacherReviewQueueViewModel(authRepository = get(), teacherRepository = get(), connectivity = get()) }
    viewModel { (submissionId: String) ->
        TeacherReviewDetailViewModel(submissionId = submissionId, teacherRepository = get(), connectivity = get())
    }

    // ── Phase 6 · X-01 Messages List / X-02 Conversation Thread / X-03 New Conversation ──────
    // Badge — no parameters; one instance per root-shell call site (Student Home, Teacher
    // Dashboard), each collecting the same MessagingRepository singleton's hot flow.
    viewModel { MessagesBadgeViewModel(authRepository = get(), messagingRepository = get()) }
    viewModel { NotificationsPanelViewModel(notificationRepository = get()) }
    viewModel { TeacherContactViewModel(authRepository = get(), messagingRepository = get()) }

    // X-01 — no parameters; the session already tells the repository who is asking.
    viewModel { MessagesListViewModel(authRepository = get(), messagingRepository = get(), connectivity = get()) }

    // X-02 — parameterised by which thread was opened.
    viewModel { (threadId: String) ->
        ConversationThreadViewModel(
            threadId = threadId,
            authRepository = get(),
            messagingRepository = get(),
            mediaUrlResolver = get(),
            connectivity = get(),
        )
    }

    // X-03 — no parameters; the screen's own permission-filtered contact list is resolved from the session.
    viewModel { NewConversationViewModel(authRepository = get(), messagingRepository = get(), connectivity = get()) }
}
