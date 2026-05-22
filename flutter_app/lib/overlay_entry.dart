import 'package:flutter/material.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';

/// Minimal orb shown as a floating overlay when the app is backgrounded.
/// Runs in its own Flutter engine — keep it lightweight.
class OverlayOrb extends StatelessWidget {
  const OverlayOrb({super.key});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => FlutterOverlayWindow.shareData('tapped'),
      child: Material(
        color: Colors.transparent,
        child: Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const RadialGradient(
              colors: [Color(0xFFD070FF), Color(0xFF5500AA)],
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFA020F0).withOpacity(0.6),
                blurRadius: 18,
                spreadRadius: 4,
              ),
            ],
          ),
          child: const Icon(Icons.blur_on, color: Colors.white70, size: 36),
        ),
      ),
    );
  }
}
