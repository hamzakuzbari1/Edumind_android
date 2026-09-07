package com.rork.eduspark.ui.screens.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.rork.eduspark.R
import com.rork.eduspark.data.model.CertificateVerification
import com.rork.eduspark.ui.components.state.ScreenStateHost
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.SkeletonDetail
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Spacing
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

/**
 * ══════════════════════════════════════════════════════════════════════════
 * A-12 · Certificate Verification — public, no auth, deep-linked.
 * ══════════════════════════════════════════════════════════════════════════
 *
 * Deliberately outside every nav graph (see `AppNavigation`) and this screen carries no
 * session dependency to match — a reader who has never opened the app must be able to land
 * here from a shared link and see a correct result. "Designed to be screenshotted and
 * shared" per the Screen Inventory, so the loaded state is a plain, unhurried card rather
 * than anything transient.
 *
 * Renders through the existing A-14 [ScreenStateHost] rather than a bespoke loading/error
 * layout — this screen's whole state shape (loading → content → not-found/offline) is
 * exactly what that component already covers.
 */
@Composable
fun CertificateVerifyScreen(
    code: String,
    modifier: Modifier = Modifier,
    viewModel: CertificateVerifyViewModel = koinViewModel(parameters = { parametersOf(code) }),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(EduTheme.colors.background)
            .safeDrawingPadding(),
    ) {
        Spacer(modifier = Modifier.height(Spacing.section))

        Column(
            horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth(),
        ) {
            BrandMark(size = 48.dp)
            Text(
                text = stringResource(R.string.a12_title),
                style = EduTheme.typography.title,
                color = EduTheme.colors.textPrimary,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = Spacing.gutter, vertical = Spacing.sm),
            )
        }

        ScreenStateHost(
            state = state.result,
            onRetry = viewModel::retry,
            isOffline = !state.isOnline,
            loading = {
                SkeletonDetail(modifier = Modifier.padding(horizontal = Spacing.gutter))
            },
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = Spacing.gutter),
        ) { certificate ->
            CertificateCard(certificate)
        }
    }
}

@Composable
private fun CertificateCard(
    certificate: CertificateVerification,
    modifier: Modifier = Modifier,
) {
    val colors = EduTheme.colors

    EduCard(modifier = modifier) {
        StatusPill(
            label = stringResource(
                if (certificate.isValid) R.string.a12_valid_badge else R.string.state_error_not_found_title
            ),
            icon = if (certificate.isValid) Icons.Filled.CheckCircle else Icons.Filled.ErrorOutline,
            contentColor = if (certificate.isValid) colors.success else colors.danger,
            containerColor = (if (certificate.isValid) colors.success else colors.danger)
                .copy(alpha = if (colors.isDark) 0.2f else 0.1f),
        )

        if (certificate.isValid) {
            CertificateField(stringResource(R.string.a12_field_holder), certificate.holderName)
            CertificateField(stringResource(R.string.a12_field_title), certificate.certificateTitle)
            CertificateField(stringResource(R.string.a12_field_level), certificate.levelOrProjectName)
            CertificateField(stringResource(R.string.a12_field_date), certificate.issueDate)
            CertificateField(stringResource(R.string.a12_field_teacher), certificate.issuingTeacher)
        }
    }
}

@Composable
private fun CertificateField(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(Spacing.xxs),
        modifier = modifier
            .fillMaxWidth()
            .padding(top = Spacing.md),
    ) {
        Text(text = label, style = EduTheme.typography.caption, color = EduTheme.colors.textMuted)
        Text(
            text = value,
            style = EduTheme.typography.bodyLg,
            color = EduTheme.colors.textPrimary,
            textAlign = TextAlign.Start,
        )
    }
}
