import 'package:flutter/material.dart';
import 'screens/home_screen.dart';
import 'screens/hub_screen.dart';
import 'screens/socialize_screen.dart';

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

  static const _screens = [
    HomeScreen(),
    HubScreen(),
    SocializeScreen(),
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
            icon: Icon(Icons.hub_outlined),
            selectedIcon: Icon(Icons.hub_rounded, color: Color(0xFFA020F0)),
            label: 'Hub',
          ),
          NavigationDestination(
            icon: Icon(Icons.people_outline_rounded),
            selectedIcon: Icon(Icons.people_rounded, color: Color(0xFFA020F0)),
            label: 'Socialize',
          ),
        ],
      ),
    );
  }
}
