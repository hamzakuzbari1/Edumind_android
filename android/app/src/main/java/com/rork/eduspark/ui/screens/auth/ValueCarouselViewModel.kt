package com.rork.eduspark.ui.screens.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rork.eduspark.core.preferences.AppPreferences
import kotlinx.coroutines.launch

/**
 * A-02 · Value Carousel.
 *
 * The carousel owns exactly one piece of persistent state — whether it has been seen —
 * so this ViewModel is deliberately tiny rather than folded into a larger shared store.
 * Skipping and finishing are the same outcome: the user has decided they do not need the
 * pitch again.
 */
class ValueCarouselViewModel(
    private val preferences: AppPreferences,
) : ViewModel() {

    fun markSeen() {
        viewModelScope.launch { preferences.setHasSeenValueCarousel(true) }
    }
}
