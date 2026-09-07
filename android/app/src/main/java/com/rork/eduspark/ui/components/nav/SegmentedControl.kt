package com.rork.eduspark.ui.components.nav

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import com.rork.eduspark.R
import com.rork.eduspark.ui.components.foundation.eduClickable
import com.rork.eduspark.ui.theme.EduTheme
import com.rork.eduspark.ui.theme.Radius
import com.rork.eduspark.ui.theme.Sizing
import com.rork.eduspark.ui.theme.Spacing

/**
 * Segmented control — two to four mutually exclusive views of the same data
 * (week/month in the planner, light/dark/system in settings, skills in the language hub).
 *
 * The order of [options] follows the reading direction automatically because it is laid
 * out with a plain [Row]: in Arabic the first option sits on the right, which is correct.
 */
@Composable
fun <T> SegmentedControl(
    options: List<T>,
    selected: T,
    onSelect: (T) -> Unit,
    labelOf: @Composable (T) -> String,
    modifier: Modifier = Modifier,
) {
    val outerShape = RoundedCornerShape(Radius.pill)
    val selectedLabel = stringResource(R.string.a11y_selected)

    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(Sizing.touchTarget)
            .background(EduTheme.colors.neutralAlpha100, outerShape)
            .border(Sizing.hairline, EduTheme.colors.border, outerShape)
            .padding(Spacing.xxs),
    ) {
        options.forEach { option ->
            val isSelected = option == selected
            val label = labelOf(option)

            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .background(
                        color = if (isSelected) EduTheme.colors.surface else EduTheme.colors.neutralAlpha100,
                        shape = outerShape,
                    )
                    .eduClickable(role = Role.Tab) { onSelect(option) }
                    .semantics {
                        this.selected = isSelected
                        if (isSelected) stateDescription = selectedLabel
                    },
            ) {
                Text(
                    text = label,
                    style = EduTheme.typography.caption,
                    color = if (isSelected) EduTheme.colors.primary else EduTheme.colors.textSecondary,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}
