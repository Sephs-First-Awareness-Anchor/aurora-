import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/hub_screen.dart';
import 'screens/habitat_space_screen.dart';
import 'screens/habitat_self_screen.dart';

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
      home: const _AppShell(),
    );
  }
}

class _AppShell extends StatefulWidget {
  const _AppShell();
  @override
  State<_AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<_AppShell> {
  int _tab = 0;

  // Aurora Build 712, App Developmental Habitat: "Aurora | Hub" becomes
  // "Aurora | Space | Self | Hub" -- four different relationships
  // between Aurora, the human, and the environment (spec section 3),
  // not just two more screens. IndexedStack keeps all four alive so
  // Space/Self state survives tab switches without a re-fetch, same as
  // Aurora/Hub already relied on.
  static const _screens = [
    HomeScreen(),
    SpaceScreen(),
    SelfScreen(),
    HubScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0F),
      body: IndexedStack(index: _tab, children: _screens),
      bottomNavigationBar: NavigationBar(
        backgroundColor: const Color(0xFF111118),
        indicatorColor: const Color(0xFFA020F0).withOpacity(0.25),
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline_rounded),
            selectedIcon: Icon(Icons.chat_bubble_rounded, color: Color(0xFFA020F0)),
            label: 'Aurora',
          ),
          NavigationDestination(
            icon: Icon(Icons.public_outlined),
            selectedIcon: Icon(Icons.public, color: Color(0xFFA020F0)),
            label: 'Space',
          ),
          NavigationDestination(
            icon: Icon(Icons.self_improvement_outlined),
            selectedIcon: Icon(Icons.self_improvement, color: Color(0xFFA020F0)),
            label: 'Self',
          ),
          NavigationDestination(
            icon: Icon(Icons.hub_outlined),
            selectedIcon: Icon(Icons.hub_rounded, color: Color(0xFFA020F0)),
            label: 'Hub',
          ),
        ],
      ),
    );
  }
}
