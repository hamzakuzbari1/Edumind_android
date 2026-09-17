package com.rork.eduspark.data.local

import android.content.Context
import android.net.Uri
import androidx.core.content.FileProvider
import com.rork.eduspark.data.model.ParentReportExport
import java.io.File

class ParentReportExportStore(
    private val context: Context,
) {
    fun save(export: ParentReportExport): Uri {
        val directory = File(context.cacheDir, EXPORT_DIR).apply { mkdirs() }
        val filename = export.filename
            .substringAfterLast('/')
            .substringAfterLast('\\')
            .replace(Regex("[^A-Za-z0-9._-]"), "_")
            .ifBlank { "eduspark-report.pdf" }
        val file = File(directory, filename)
        file.writeBytes(export.bytes)
        return FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file,
        )
    }

    private companion object {
        const val EXPORT_DIR = "parent-exports"
    }
}
