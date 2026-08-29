package com.rork.eduspark.ui.components.scaffold

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rork.eduspark.ui.components.nav.EduTopBar
import com.rork.eduspark.ui.theme.EduTheme

/**
 * The app's screen shell.
 *
 * Encodes the navigation rule from Rork Knowledge §5 / Master Plan §1b:
 *
 *   "Handle the Android hardware back button on every screen — but never make it the
 *    only way back. Every screen also has a visible back affordance, because iOS has no
 *    hardware back button."
 *
 * [onBack] therefore wires BOTH at once: the [BackHandler] for the hardware/gesture back
 * and the TopBar's visible arrow. A screen cannot accidentally implement one without the
 * other, which is exactly the drift that makes an iOS port expensive later.
 *
 * Edge-swipe back mirrors automatically in RTL — the system predictive-back gesture reads
 * layout direction from the per-app locale, which is why the locale is applied at the
 * framework level rather than only inside the composition.
 */
@Composable
fun EduScaffold(
    title: String,
    modifier: Modifier = Modifier,
    onBack: (() -> Unit)? = null,
    actions: @Composable RowScope.() -> Unit = {},
    snackbarHostState: SnackbarHostState = remember { SnackbarHostState() },
    bottomBar: @Composable () -> Unit = {},
    floatingActionButton: @Composable () -> Unit = {},
    contentPadding: PaddingValues = PaddingValues(0.dp),
    content: @Composable (PaddingValues) -> Unit,
) {
    // Hardware / gesture back — enabled only when this screen actually owns a back action.
    BackHandler(enabled = onBack != null) { onBack?.invoke() }

    Scaffold(
        topBar = { EduTopBar(title = title, onBack = onBack, actions = actions) },
        bottomBar = bottomBar,
        floatingActionButton = floatingActionButton,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
        containerColor = EduTheme.colors.background,
        contentColor = EduTheme.colors.textPrimary,
        modifier = modifier.fillMaxSize(),
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {
            content(contentPadding)
        }
    }
}

/**
 * Root-of-a-tab shell: no back arrow, and hardware back is left to the navigation host
 * so the standard "back exits the app from the start destination" behaviour is preserved.
 */
@Composable
fun EduRootScaffold(
    title: String,
    modifier: Modifier = Modifier,
    actions: @Composable RowScope.() -> Unit = {},
    bottomBar: @Composable () -> Unit = {},
    snackbarHostState: SnackbarHostState = remember { SnackbarHostState() },
    content: @Composable (PaddingValues) -> Unit,
) {
    Scaffold(
        topBar = { EduTopBar(title = title, onBack = null, actions = actions) },
        bottomBar = bottomBar,
        snackbarHost = { SnackbarHost(hostState = snackbarHostState) },
        containerColor = EduTheme.colors.background,
        contentColor = EduTheme.colors.textPrimary,
        modifier = modifier.fillMaxSize(),
    ) { innerPadding ->
        content(innerPadding)
    }
}
