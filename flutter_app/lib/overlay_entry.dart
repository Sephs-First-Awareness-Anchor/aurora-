import 'package:flutter/material.dart';

/// Visual representation of the floating orb.
/// The actual floating window is rendered natively by OverlayService.kt;
/// this widget is kept for in-app use (e.g. BACKGROUND state orb).
class OverlayOrb extends StatelessWidget {
  const OverlayOrb({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
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
    );
  }
}
