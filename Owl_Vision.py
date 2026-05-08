package com.example.stereocameraprobe

import android.Manifest import android.content.pm.PackageManager import android.hardware.camera2.CameraCharacteristics import android.hardware.camera2.CameraManager import android.os.Build import android.os.Bundle import android.util.Size import android.widget.TextView import androidx.activity.ComponentActivity import androidx.activity.result.contract.ActivityResultContracts import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {

private lateinit var output: TextView

private val requestCameraPermission = registerForActivityResult(
    ActivityResultContracts.RequestPermission()
) { granted ->
    if (granted) runCameraProbe()
    else output.text = "Camera permission denied. The probe needs camera access to inspect the hardware."
}

override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    output = TextView(this).apply {
        textSize = 15
        setPadding(32, 48, 32, 32)
        text = "Stereo Camera Probe\n\nChecking permission..."
    }
    setContentView(output)

    if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
        == PackageManager.PERMISSION_GRANTED
    ) {
        runCameraProbe()
    } else {
        requestCameraPermission.launch(Manifest.permission.CAMERA)
    }
}

private fun runCameraProbe() {
    val cameraManager = getSystemService(CameraManager::class.java)
    val report = StringBuilder()

    report.appendLine("Stereo Camera Probe")
    report.appendLine("Device: ${Build.MANUFACTURER} ${Build.MODEL}")
    report.appendLine("Android API: ${Build.VERSION.SDK_INT}")
    report.appendLine()

    val cameraIds = cameraManager.cameraIdList.toList()
    report.appendLine("Visible camera IDs: ${cameraIds.joinToString()}")
    report.appendLine()

    val rearLogicalMultiCameras = mutableListOf<LogicalMultiCameraInfo>()
    val rearSingleCameras = mutableListOf<String>()

    for (cameraId in cameraIds) {
        val chars = cameraManager.getCameraCharacteristics(cameraId)
        val facing = chars.get(CameraCharacteristics.LENS_FACING)
        val capabilities = chars.get(CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES)
            ?.toSet()
            ?: emptySet()

        val isBack = facing == CameraCharacteristics.LENS_FACING_BACK
        val isLogicalMulti = capabilities.contains(
            CameraCharacteristics.REQUEST_AVAILABLE_CAPABILITIES_LOGICAL_MULTI_CAMERA
        )

        val physicalIds = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            chars.physicalCameraIds.toList().sorted()
        } else {
            emptyList()
        }

        report.appendLine("Camera ID: $cameraId")
        report.appendLine("  Facing: ${facingLabel(facing)}")
        report.appendLine("  Logical multi-camera: $isLogicalMulti")
        report.appendLine("  Physical camera IDs: ${physicalIds.ifEmpty { listOf("none exposed") }.joinToString()}")
        report.appendLine("  Hardware level: ${hardwareLevelLabel(chars.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL))}")
        report.appendLine("  JPEG sizes: ${topJpegSizes(chars).joinToString()}")
        report.appendLine()

        if (isBack && isLogicalMulti && physicalIds.size >= 2) {
            rearLogicalMultiCameras.add(
                LogicalMultiCameraInfo(
                    logicalId = cameraId,
                    physicalIds = physicalIds,
                    hardwareLevel = hardwareLevelLabel(
                        chars.get(CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL)
                    )
                )
            )
        }

        if (isBack && !isLogicalMulti) {
            rearSingleCameras.add(cameraId)
        }
    }

    report.appendLine("===== Stereo Feasibility Verdict =====")

    if (rearLogicalMultiCameras.isNotEmpty()) {
        report.appendLine("PASS: This phone exposes at least one rear logical multi-camera with 2+ physical cameras.")
        report.appendLine()
        report.appendLine("Best next step: build a dual physical-camera capture session from one logical camera.")
        report.appendLine()
        rearLogicalMultiCameras.forEach { info ->
            report.appendLine("Candidate logical rear camera: ${info.logicalId}")
            report.appendLine("  Physical pair candidates: ${pairList(info.physicalIds)}")
            report.appendLine("  Hardware level: ${info.hardwareLevel}")
        }
    } else if (rearSingleCameras.size >= 2) {
        report.appendLine("MAYBE: This phone exposes multiple rear camera IDs, but not as a logical multi-camera pair.")
        report.appendLine("That may still allow separate-camera capture on some devices, but it is less reliable.")
        report.appendLine("Rear camera IDs found: ${rearSingleCameras.joinToString()}")
    } else {
        report.appendLine("FAIL for true stereo capture: No rear logical multi-camera with 2+ physical cameras was exposed.")
        report.appendLine("Fallback path: take two photos from slightly different phone positions and compute depth from motion.")
    }

    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
        report.appendLine()
        report.appendLine("===== Concurrent Camera Sets =====")
        val concurrentSets = cameraManager.concurrentCameraIds
        if (concurrentSets.isEmpty()) {
            report.appendLine("No concurrent camera sets reported.")
        } else {
            concurrentSets.forEachIndexed { index, set ->
                report.appendLine("Set ${index + 1}: ${set.joinToString()}")
            }
        }
    }

    output.text = report.toString()
}

private fun facingLabel(facing: Int?): String = when (facing) {
    CameraCharacteristics.LENS_FACING_FRONT -> "front"
    CameraCharacteristics.LENS_FACING_BACK -> "back"
    CameraCharacteristics.LENS_FACING_EXTERNAL -> "external"
    else -> "unknown"
}

private fun hardwareLevelLabel(level: Int?): String = when (level) {
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LEGACY -> "LEGACY"
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_LIMITED -> "LIMITED"
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_FULL -> "FULL"
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_3 -> "LEVEL_3"
    CameraCharacteristics.INFO_SUPPORTED_HARDWARE_LEVEL_EXTERNAL -> "EXTERNAL"
    else -> "unknown"
}

private fun topJpegSizes(chars: CameraCharacteristics): List<String> {
    val map = chars.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
        ?: return emptyList()

    return map.getOutputSizes(android.graphics.ImageFormat.JPEG)
        ?.sortedByDescending { it.width.toLong() * it.height.toLong() }
        ?.take(4)
        ?.map(Size::toPrettyString)
        ?: emptyList()
}

private fun Size.toPrettyString(): String = "${width}x${height}"

private fun pairList(ids: List<String>): String {
    val pairs = mutableListOf<String>()
    for (i in ids.indices) {
        for (j in i + 1 until ids.size) {
            pairs.add("${ids[i]} + ${ids[j]}")
        }
    }
    return pairs.joinToString()
}

data class LogicalMultiCameraInfo(
    val logicalId: String,
    val physicalIds: List<String>,
    val hardwareLevel: String
)

}
