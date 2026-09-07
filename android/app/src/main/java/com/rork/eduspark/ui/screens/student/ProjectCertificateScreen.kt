package com.rork.eduspark.ui.screens.student

import android.content.Context
import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.CertificateVerification
import com.rork.eduspark.ui.components.action.PrimaryButton
import com.rork.eduspark.ui.components.action.SecondaryButton
import com.rork.eduspark.ui.components.input.EduChip
import com.rork.eduspark.ui.components.scaffold.EduScaffold
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.SkeletonCard
import com.rork.eduspark.ui.screens.auth.BrandMark
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * PJ-11 · Project Certificate.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * The certificate card renders straight from [CertificateVerification] — the SAME model/A-12
 * verification path this app already ships, never a parallel one. "Verify" pushes the actual
 * [com.rork.eduspark.ui.navigation.Routes.CERTIFICATE_VERIFY] screen with this certificate's
 * own code, so the student sees their certificate resolve through the exact public path a
 * parent or interviewer would use. Share reuses the same real, permission-free
 * `Intent.ACTION_SEND` (`text/plain`) [PortfolioScreen] uses. Image export stays an honest
 * MOCK — [ExportMockDialog] — because no bitmap-capture/FileProvider pipeline exists in this
 * slice and none should be added just to back this one button.
 */
@Composable
fun ProjectCertificateScreen(
    projectId: String,
    onBack: () -> Unit,
    onVerify: (code: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: ProjectCertificateViewModel = koinViewModel(parameters = { parametersOf(projectId) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    EduScaffold(title = stringResource(R.string.pj11_title), onBack = onBack, modifier = modifier) { _ ->
        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = { CertificateSkeleton() },
            modifier = Modifier.fillMaxSize(),
        ) { data ->
            CertificateContent(
                certificate = data.certificate,
                onShare = { shareCertificate(context, data.certificate, data.code) },
                onVerify = { onVerify(data.code) },
                onExportImage = viewModel::openExportDialog,
            )
        }
    }

    if (state.showExportDialog) {
        ExportMockDialog(onDismiss = viewModel::dismissExportDialog)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun CertificateContent(
    certificate: CertificateVerification,
    onShare: () -> Unit,
    onVerify: () -> Unit,
    onExportImage: () -> Unit,
) {
    val colors = EduTheme.colors

    LazyColumn(
        contentPadding = PaddingValues(horizontal = Spacing.gutter, vertical = Spacing.md),
        modifier = Modifier.fillMaxSize(),
    ) {
        item {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .fillMaxWidth()
                    .background(colors.surface, RoundedCornerShape(Radius.md))
                    .border(Sizing.hairline, colors.primary, RoundedCornerShape(Radius.md))
                    .padding(Spacing.section),
            ) {
                BrandMark(size = 44.dp)
                Text(
                    text = stringResource(R.string.pj11_brand_line),
                    style = EduTheme.typography.caption,
                    color = colors.primary,
                    modifier = Modifier.padding(top = Spacing.xs),
                )
                Text(
                    text = certificate.certificateTitle,
                    style = EduTheme.typography.brandTitle,
                    color = colors.textPrimary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = Spacing.md),
                )

                CertificateField(stringResource(R.string.pj11_field_holder), certificate.holderName)
                CertificateField(stringResource(R.string.pj11_field_project), certificate.levelOrProjectName)
                CertificateField(stringResource(R.string.pj11_field_date), certificate.issueDate)
                CertificateField(stringResource(R.string.pj11_field_issuer), certificate.issuingTeacher)

                if (certificate.skills.isNotEmpty()) {
                    Text(
                        text = stringResource(R.string.pj11_field_skills),
                        style = EduTheme.typography.caption,
                        color = colors.textSecondary,
                        modifier = Modifier.padding(top = Spacing.md),
                    )
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                        verticalArrangement = Arrangement.spacedBy(Spacing.xs),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = Spacing.xxs),
                    ) {
                        certificate.skills.forEach { skill -> EduChip(label = skill, selected = false, onClick = {}, enabled = false) }
                    }
                }

                if (certificate.isValid) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(Spacing.xs),
                        modifier = Modifier
                            .padding(top = Spacing.section)
                            .background(colors.primaryContainer, RoundedCornerShape(Radius.pill))
                            .padding(horizontal = Spacing.md, vertical = Spacing.sm),
                    ) {
                        Icon(Icons.Filled.Verified, contentDescription = null, tint = colors.primary, modifier = Modifier.size(Sizing.iconSm))
                        Text(stringResource(R.string.pj11_verified_label), style = EduTheme.typography.caption, color = colors.primary)
                    }
                }
            }
        }

        item {
            Column(modifier = Modifier.padding(top = Spacing.section)) {
                PrimaryButton(
                    text = stringResource(R.string.pj11_verify_action),
                    onClick = onVerify,
                    modifier = Modifier.fillMaxWidth(),
                )
                Row(horizontalArrangement = Arrangement.spacedBy(Spacing.sm), modifier = Modifier.padding(top = Spacing.xs)) {
                    SecondaryButton(
                        text = stringResource(R.string.pj11_share),
                        onClick = onShare,
                        leadingIcon = Icons.Filled.Share,
                        modifier = Modifier.weight(1f),
                    )
                    SecondaryButton(
                        text = stringResource(R.string.pj11_export_image),
                        onClick = onExportImage,
                        leadingIcon = Icons.Filled.Image,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun CertificateField(label: String, value: String) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = Spacing.md),
    ) {
        Text(text = label, style = EduTheme.typography.caption, color = EduTheme.colors.textSecondary)
        Text(
            text = value,
            style = EduTheme.typography.bodyLg,
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = Spacing.xxs),
        )
    }
}

/** The honest MOCK boundary — no bitmap was captured, no file was written; see this file's own doc comment. */
@Composable
private fun ExportMockDialog(onDismiss: () -> Unit) {
    val colors = EduTheme.colors
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(text = stringResource(R.string.pj11_export_mock_title), style = EduTheme.typography.title, color = colors.textPrimary) },
        text = { Text(text = stringResource(R.string.pj11_export_mock_body), style = EduTheme.typography.body, color = colors.textSecondary) },
        confirmButton = { PrimaryButton(text = stringResource(R.string.common_done), onClick = onDismiss) },
        containerColor = colors.surface,
        titleContentColor = colors.textPrimary,
        textContentColor = colors.textSecondary,
    )
}

@Composable
private fun CertificateSkeleton() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = Spacing.gutter, vertical = Spacing.md),
    ) {
        SkeletonCard()
    }
}

private fun shareCertificate(context: Context, certificate: CertificateVerification, code: String) {
    val text = buildString {
        append(certificate.certificateTitle)
        append(" — ")
        append(certificate.levelOrProjectName)
        append("\n")
        append(certificate.holderName)
        append(" · ")
        append(certificate.issueDate)
        append("\n")
        append(code)
    }
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, text)
    }
    context.startActivity(Intent.createChooser(intent, null))
}

