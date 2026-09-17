package com.rork.eduspark.ui.screens.teacher

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.core.result.AppError
import com.rork.eduspark.data.model.TeacherProfessionalDocument
import com.rork.eduspark.data.model.TeacherQualification
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel

/**
 * Teaching Page / Qualifications (صفحة التدريس) — intentionally limited.
 * Shows existing qualifications read-only; professional documents open via MediaUrlResolver.
 */
@Composable
fun TeacherProfilePreviewScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: TeacherProfileViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val snackbarHostState = remember { SnackbarHostState() }
    val offlineBody = stringResource(R.string.state_error_network_body)
    val serverBody = stringResource(R.string.state_error_server_body)
    val unauthorizedBody = stringResource(R.string.state_error_unauthorized_body)
    val notFoundBody = stringResource(R.string.state_error_not_found_body)
    val unknownBody = stringResource(R.string.state_error_unknown_body)

    LaunchedEffect(viewModel) {
        viewModel.events.collect { event ->
            when (event) {
                is TeacherProfileEvent.OpenExternalDocument -> {
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(event.url))
                    runCatching { context.startActivity(intent) }
                        .onFailure { snackbarHostState.showSnackbar(unknownBody) }
                }
                is TeacherProfileEvent.DocumentOpenFailed -> {
                    val message = when (event.error) {
                        AppError.Offline, AppError.Network -> offlineBody
                        AppError.Server -> serverBody
                        AppError.SessionExpired, AppError.Forbidden -> unauthorizedBody
                        AppError.NotFound -> notFoundBody
                        else -> unknownBody
                    }
                    snackbarHostState.showSnackbar(message)
                }
                else -> Unit
            }
        }
    }

    EduScaffold(
        title = stringResource(R.string.tc16_teaching_title),
        onBack = onBack,
        snackbarHostState = snackbarHostState,
        modifier = modifier,
    ) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { TeacherPreviewSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            TeacherTeachingPageContent(
                qualifications = data.qualifications,
                documents = data.professionalDocuments,
                isResolvingDocument = state.isResolvingDocument,
                onOpenDocument = viewModel::openProfessionalDocument,
                onDone = onBack,
            )
        }
    }
}

@Composable
private fun TeacherTeachingPageContent(
    qualifications: List<TeacherQualification>,
    documents: List<TeacherProfessionalDocument>,
    isResolvingDocument: Boolean,
    onOpenDocument: (String) -> Unit,
    onDone: () -> Unit,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            TeachingPageVisual()
            Text(
                text = stringResource(R.string.tc16_teaching_heading),
                style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
            Text(
                text = stringResource(R.string.tc16_teaching_body),
                style = EduTheme.typography.body,
                color = colors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.xs, bottom = Spacing.md),
            )
        }

        if (qualifications.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.tc16_qualifications_empty),
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = Spacing.md),
                )
            }
        } else {
            items(qualifications, key = { it.id }) { qualification ->
                TeachingQualificationRow(qualification)
            }
        }

        item {
            Text(
                text = stringResource(R.string.tc16_documents_section),
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.ExtraBold),
                color = colors.textPrimary,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.md, bottom = Spacing.sm),
            )
        }

        if (documents.isEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.tc16_documents_empty),
                    style = EduTheme.typography.caption,
                    color = colors.textMuted,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = Spacing.md),
                )
            }
        } else {
            items(documents, key = { it.id }) { document ->
                TeachingDocumentRow(
                    document = document,
                    enabled = !isResolvingDocument,
                    onOpen = { onOpenDocument(document.id) },
                )
            }
        }

        item {
            SecondaryButton(
                text = stringResource(R.string.tc16_teaching_ok),
                onClick = onDone,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = Spacing.sm),
            )
        }
    }
}

@Composable
private fun TeachingPageVisual() {
    val colors = EduTheme.colors
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .fillMaxWidth()
            .height(120.dp)
            .background(colors.primaryContainer, RoundedCornerShape(Radius.md)),
    ) {
        Canvas(modifier = Modifier.size(80.dp, 70.dp)) {
            val stroke = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round)
            val page = Path().apply {
                addRoundRect(
                    androidx.compose.ui.geometry.RoundRect(
                        left = size.width * 0.2f,
                        top = size.height * 0.12f,
                        right = size.width * 0.8f,
                        bottom = size.height * 0.88f,
                        radiusX = 6.dp.toPx(),
                        radiusY = 6.dp.toPx(),
                    )
                )
            }
            drawPath(page, color = androidx.compose.ui.graphics.Color.White)
            drawPath(page, color = colors.primary, style = stroke)
            val lineColor = colors.primary.copy(alpha = 0.35f)
            val startX = size.width * 0.32f
            val endFull = size.width * 0.68f
            drawLine(lineColor, androidx.compose.ui.geometry.Offset(startX, size.height * 0.34f), androidx.compose.ui.geometry.Offset(endFull, size.height * 0.34f), strokeWidth = 2.dp.toPx())
            drawLine(lineColor, androidx.compose.ui.geometry.Offset(startX, size.height * 0.48f), androidx.compose.ui.geometry.Offset(size.width * 0.6f, size.height * 0.48f), strokeWidth = 2.dp.toPx())
            drawLine(lineColor, androidx.compose.ui.geometry.Offset(startX, size.height * 0.62f), androidx.compose.ui.geometry.Offset(size.width * 0.52f, size.height * 0.62f), strokeWidth = 2.dp.toPx())
        }
    }
}

@Composable
private fun TeachingQualificationRow(qualification: TeacherQualification) {
    val colors = EduTheme.colors
    val label = listOfNotNull(
        qualification.title.ifBlank { null },
        qualification.institution.ifBlank { null },
        qualification.year,
    ).joinToString(" · ")
    EduCard(
        modifier = Modifier.padding(bottom = Spacing.sm),
        containerColor = colors.surface.copy(alpha = 0.7f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = label.ifBlank { qualification.title },
                style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                color = colors.textPrimary,
                modifier = Modifier
                    .weight(1f)
                    .padding(end = Spacing.sm),
            )
            Text(
                text = stringResource(R.string.tc_coming_soon_title),
                style = EduTheme.typography.caption,
                color = colors.textMuted,
            )
        }
    }
}

@Composable
private fun TeachingDocumentRow(
    document: TeacherProfessionalDocument,
    enabled: Boolean,
    onOpen: () -> Unit,
) {
    val colors = EduTheme.colors
    val title = document.title.ifBlank {
        document.originalFilename.orEmpty().ifBlank { stringResource(R.string.tc17_media_document) }
    }
    EduCard(
        modifier = Modifier
            .padding(bottom = Spacing.sm)
            .then(
                if (enabled) Modifier.eduClickable(onClickLabel = title, onClick = onOpen)
                else Modifier,
            ),
        containerColor = colors.surface.copy(alpha = 0.7f),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.weight(1f).padding(end = Spacing.sm)) {
                Text(
                    text = title,
                    style = EduTheme.typography.body.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.tc16_document_uploaded),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            Text(
                text = stringResource(R.string.tc16_preview),
                style = EduTheme.typography.caption.copy(fontWeight = FontWeight.Bold),
                color = colors.primary,
            )
        }
    }
}

@Composable
private fun TeacherPreviewSkeleton() {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.sm),
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard(modifier = Modifier.fillMaxWidth().height(120.dp))
        SkeletonCard(modifier = Modifier.fillMaxWidth().height(72.dp))
        SkeletonCard(modifier = Modifier.fillMaxWidth().height(72.dp))
    }
}
