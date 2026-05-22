import 'package:flutter/material.dart';
import 'overlay_entry.dart';
import 'screens/home_screen.dart';

/// Overlay entry point — runs in a separate Flutter engine managed by
/// flutter_overlay_window.  Keep this lightweight.
@pragma('vm:entry-point')
void overlayMain() {
  runApp(
    const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        backgroundColor: Colors.transparent,
        body: OverlayOrb(),
      ),
    ),
  );
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const AuroraApp());
}

class AuroraApp extends StatelessWidget {
  const AuroraApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Aurora',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        colorSchemeSeed: const Color(0xFFA020F0),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFF0D0D0F),
      ),
      home: const HomeScreen(),
    );
  }
}
