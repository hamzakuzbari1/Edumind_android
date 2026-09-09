package com.rork.eduspark.ui.screens.parent

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.School
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.rork.eduspark.R
import com.rork.eduspark.data.model.ParentLinkedStudent
import com.rork.eduspark.ui.components.surface.EduCard
import com.rork.eduspark.ui.components.surface.StatusPill
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

@Composable
internal fun ParentAvatar(
    initial: String,
    modifier: Modifier = Modifier,
    containerColor: Color = EduTheme.colors.primaryContainer,
    contentColor: Color = EduTheme.colors.primary,
) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .size(Sizing.avatar)
            .background(containerColor, CircleShape),
    ) {
        Text(
            text = initial,
            style = EduTheme.typography.title.copy(fontWeight = FontWeight.ExtraBold),
            color = contentColor,
        )
    }
}

@Composable
internal fun ParentLinkedStudentCard(
    student: ParentLinkedStudent,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    action: @Composable (() -> Unit)? = null,
) {
    val colors = EduTheme.colors
    EduCard(modifier = modifier, onClick = onClick) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(Spacing.sm),
        ) {
            ParentAvatar(
                initial = student.avatarInitial,
                containerColor = colors.primaryContainer,
                contentColor = colors.primary,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = student.displayName,
                    style = EduTheme.typography.bodyLg.copy(fontWeight = FontWeight.SemiBold),
                    color = colors.textPrimary,
                )
                Text(
                    text = stringResource(R.string.pr_linked_student_grade_section, student.gradeLabel, student.sectionLabel),
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
                Text(
                    text = student.schoolName,
                    style = EduTheme.typography.caption,
                    color = colors.textSecondary,
                )
            }
            if (action != null) {
                action()
            } else {
                StatusPill(
                    label = student.statusLabel,
                    icon = Icons.Filled.School,
                    contentColor = colors.success,
                    containerColor = colors.success.copy(alpha = 0.14f),
                )
            }
        }
    }
}

