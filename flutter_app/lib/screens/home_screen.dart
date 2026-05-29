import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';

import '../aurora_bridge.dart';
import '../widgets/aurora_orb.dart';

const _purple = Color(0xFFA020F0);
const _bg     = Color(0xFF0D0D0F);

class ChatMsg {
  final String text;
  final bool isUser;
  ChatMsg(this.text, {required this.isUser});
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with TickerProviderStateMixin, WidgetsBindingObserver {

  // ── Embodiment state ────────────────────────────────────────────────────
  String _embState = 'DORMANT';

  // ── Orb animation ───────────────────────────────────────────────────────
  late AnimationController _pulseCtrl;
  late Animation<double>   _pulseAnim;

  // ── Chat ───────────────────────────────────────────────────────────……[...]
  final List<ChatMsg>         _msgs       = [];
  final TextEditingController _textCtrl   = TextEditingController();
  final ScrollController      _scrollCtrl = ScrollController();

  // ── AI state ──────────────────────────────────────────────────────────…[...]
  bool   _aiReady   = false;
  String _statusTxt = 'Starting Aurora…';

  // ── Aurora emotional axis state (X/T/N/B/A, each 0.0–1.0) ───────────────
  Map<String, double> _axisState = {
    'X': 0.5, 'T': 0.5, 'N': 0.5, 'B': 0.5, 'A': 0.5,
  };

  // ── STT / TTS state ─────────────────────────────────────────────────────
  bool   _listening   = false;
  bool   _speaking    = false;
  bool   _quietMode   = false;
  String _partialText = '';

  // ── Conversation window ──────────────────────────────────────────────────
  static const _convSec = 30;
  Timer? _convTimer;
  bool   _inConversation = false;
  bool   _screenObserverReady = false;

  // ── Bridge events ────────────────────────────────────────────────────────
  StreamSubscription? _bridgeSub;

  // ─────────────────────────────────────────────────────────────……[...]

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    )..repeat(reverse: true);
    _pulseAnim = CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut);

    _init();
  }

  Future<void> _init() async {
    _listenBridgeEvents();
    setState(() => _embState = 'BACKGROUND');
    _refreshScreenObserverStatus();
    _startListening();
  }

  void _listenBridgeEvents() {
    _bridgeSub = AuroraBridge.events.listen((event) {
      final source = event['source'] as String? ?? 'aurora';
      final type   = event['type']   as String? ?? '';
      final text   = event['text']   as String? ?? '';

      switch (source) {
        case 'stt':
          _handleSttEvent(type, text, event['final'] as bool? ?? false);
        case 'tts':
          if (type == 'done' && mounted) {
            setState(() => _speaking = false);
            _pulseCtrl.repeat(reverse: true);
            if (_embState != 'DORMANT') _startListening();
          } else if (type == 'word' && mounted && _speaking) {
            _kickPulse();
          }
        case 'permission':
          if (type == 'update' && mounted) {
            final map = event['granted_map'] as Map?;
            if (map != null) {
              final mic = map['microphone'] == true;
              if (mic && !_speaking) _startListening();
            }
          }
        case 'camera':
          if (type == 'captured' && mounted) {
            setState(() => _statusTxt = 'Vision captured!');
            Future.delayed(const Duration(seconds: 2), () {
              if (mounted) setState(() => _statusTxt = _inConversation ? 'Listening…' : 'Listening for "Aurora"…');
            });
          }
        case 'screen':
          if (type == 'observed' && mounted) {
            setState(() => _screenObserverReady = true);
          }
        default: // aurora service events
          switch (type) {
            case 'axis_state':
              if (mounted) {
                setState(() {
                  _axisState = {
                    'X': (event['X'] as double?) ?? _axisState['X']!,
                    'T': (event['T'] as double?) ?? _axisState['T']!,
                    'N': (event['N'] as double?) ?? _axisState['N']!,
                    'B': (event['B'] as double?) ?? _axisState['B']!,
                    'A': (event['A'] as double?) ?? _axisState['A']!,
                  };
                });
              }
            case 'ready':
              if (mounted) {
                setState(() { _aiReady = true; _statusTxt = 'Listening…'; });
              }
              _speak('Aurora is online.');
            case 'proactive':
              // Curiosity session completed — Aurora reports back unprompted.
              if (mounted && text.isNotEmpty) {
                setState(() {
                  _msgs.add(ChatMsg(text, isUser: false));
                  _statusTxt = _inConversation ? 'Listening…' : 'Listening for "Aurora"…';
                });
                _scrollToBottom();
                if (!_quietMode) _speak(text);
              }
            case 'error':
              if (mounted) {
                // Show the real error message so it's visible for diagnosis.
                final short = text.length > 120 ? '${text.substring(0, 120)}…' : text;
                setState(() { _aiReady = false; _statusTxt = 'Boot error: $short'; });
              }
            default:
              break;
          }
      }
    });
  }

  void _handleSttEvent(String type, String text, bool isFinal) {
    if (!mounted) return;
    switch (type) {
      case 'partial':
        if (text.isNotEmpty) setState(() => _partialText = text);
      case 'result':
        if (isFinal) {
          setState(() { _partialText = ''; _listening = false; });
          _processRecognizedText(text);
        }
      case 'error':
        setState(() { _listening = false; _partialText = ''; });
        if (!_speaking && _embState != 'DORMANT') {
          Future.delayed(const Duration(milliseconds: 600), _startListening);
        }
    }
  }

  static final _quietOnRe  = RegExp(r'\b(quiet\s*mode|go\s*quiet|be\s*quiet|silent\s*mode|silence)\b', caseSensitive: false);
  static final _quietOffRe = RegExp(r'\b(voice\s*on|speak\s*again|unquiet|come\s*back|talk\s*again|normal\s*mode)\b', caseSensitive: false);

  void _toggleQuietMode(bool on) {
    setState(() => _quietMode = on);
    final msg = on ? 'Quiet mode on. I\'ll keep watching.' : 'Voice on.';
    if (!on) {
      _speak(msg);
    } else {
      // Show feedback in chat without speaking
      setState(() => _msgs.add(ChatMsg(msg, isUser: false)));
      _scrollToBottom();
      if (!_speaking) _startListening();
    }
  }

  void _processRecognizedText(String words) {
    final lower = words.toLowerCase().trim();
    if (lower.isEmpty) {
      if (!_speaking) _startListening();
      return;
    }

    // Quiet mode toggle commands — handled before anything else.
    if (_quietOffRe.hasMatch(lower)) { _toggleQuietMode(false); return; }
    if (_quietOnRe.hasMatch(lower))  { _toggleQuietMode(true);  return; }

    // If we're already in a conversation, respond to EVERYTHING heard.
    // If not, only respond if "Aurora" is mentioned.
    if (_inConversation || _embState == 'SUMMONED') {
      _resetConversationWindow();
      _sendMessage(words);
    } else if (lower.contains('aurora')) {
      final idx   = lower.indexOf('aurora');
      final after = words.substring(idx + 6).trim();
      _summon();
      if (after.isNotEmpty) {
        Future.delayed(const Duration(milliseconds: 300), () => _sendMessage(after));
      } else {
        _speak('Yes?');
      }
    } else {
      // Not for us, keep listening
      if (!_speaking) _startListening();
    }
  }

  // ── Embodiment transitions ────────────────────────────────────────────────

  void _summon() {
    if (_embState == 'SUMMONED') return;
    setState(() => _embState = 'SUMMONED');
    AuroraBridge.setState('SUMMONED');
    AuroraBridge.stopOverlay();
    _startConversationWindow();
  }

  Future<void> _background() async {
    _convTimer?.cancel();
    _inConversation = false;
    AuroraBridge.stopListening();
    setState(() {
      _embState  = 'BACKGROUND';
      _listening = false;
      _statusTxt = 'Listening for "Aurora"…';
    });
    AuroraBridge.setState('BACKGROUND');
    final started = await AuroraBridge.startOverlay();
    if (!started) {
      setState(() => _statusTxt = 'Overlay permission needed');
    }
  }

  Future<void> _refreshScreenObserverStatus() async {
    final ready = await AuroraBridge.hasScreenObserverPermission();
    if (!mounted) return;
    setState(() => _screenObserverReady = ready);
  }

  Future<void> _requestScreenObserver() async {
    await AuroraBridge.requestScreenObserverPermission();
    if (!mounted) return;
    setState(() => _statusTxt = 'Enable Aurora screen observer, then return');
  }

  void _startConversationWindow() {
    _convTimer?.cancel();
    _inConversation = true;
    _convTimer = Timer(const Duration(seconds: _convSec), () {
      if (mounted && _embState == 'SUMMONED') _background();
    });
  }

  void _resetConversationWindow() {
    if (_inConversation) _startConversationWindow();
  }

  // ── STT ───────────────────────────────────────────────────────────……[...]

  void _startListening() {
    if (_listening || _speaking || _embState == 'DORMANT') return;
    setState(() { _listening = true; _partialText = ''; });
    AuroraBridge.startListening();
  }

  // ── TTS ───────────────────────────────────────────────────────────……[...]

  Future<void> _speak(String text) async {
    if (text.isEmpty) return;
    AuroraBridge.stopListening();
    setState(() { _speaking = true; _listening = false; });
    await AuroraBridge.speak(text);
  }

  // Snap pulse to 1.0 on each spoken word, then decay — driven by TTS onRangeStart.
  void _kickPulse() {
    _pulseCtrl
      ..stop()
      ..animateTo(1.0,
          duration: const Duration(milliseconds: 80),
          curve: Curves.easeOut)
      .then((_) {
        if (!mounted) return;
        if (_speaking) {
          _pulseCtrl.animateTo(0.20,
              duration: const Duration(milliseconds: 400),
              curve: Curves.easeIn);
        } else {
          _pulseCtrl.repeat(reverse: true);
        }
      });
  }

  // ── Message send ────────────────────────────────────────────────────────……[...]

  Future<void> _sendMessage(String text) async {
    text = text.trim();
    if (text.isEmpty) return;
    _textCtrl.clear();
    AuroraBridge.stopListening();

    setState(() {
      _listening = false;
      _msgs.add(ChatMsg(text, isUser: true));
      _statusTxt = 'Thinking…';
    });
    _scrollToBottom();

    final reply = await AuroraBridge.sendMessage(text);
    if (!mounted) return;

    setState(() {
      _msgs.add(ChatMsg(reply, isUser: false));
      _statusTxt = _inConversation ? 'Listening…' : 'Listening for "Aurora"…';
    });
    _scrollToBottom();
    if (_quietMode) {
      _startListening();
    } else {
      _speak(reply);
    }
    _resetConversationWindow();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  // ── App lifecycle ────────────────────────────────────────────────────────…[...]

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) async {
    if (state == AppLifecycleState.paused && _embState != 'DORMANT') {
      await _background();
    } else if (state == AppLifecycleState.resumed) {
      await _refreshScreenObserverStatus();
      final wasTapped = await AuroraBridge.consumeOverlayTap();
      if (wasTapped) {
        _summon();
      } else if (_embState == 'BACKGROUND') {
        AuroraBridge.stopOverlay();
        _startListening();
      }
    }
  }

  // ── Build ───────────────────────────────────────────────────────────[...]

  @override
  Widget build(BuildContext context) {
    final isSummoned = _embState == 'SUMMONED';
    final orbState   = _speaking   ? OrbState.speaking
                     : _listening  ? OrbState.listening
                     : !_aiReady   ? OrbState.thinking
                     : OrbState.dormant;

    final statusWidget = AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Text(
        _partialText.isNotEmpty ? _partialText : _statusTxt,
        key: ValueKey(_partialText.isNotEmpty),
        style: TextStyle(
          color: Colors.white.withOpacity(0.6),
          fontSize: 13,
          fontStyle: _partialText.isNotEmpty ? FontStyle.italic : FontStyle.normal,
        ),
        textAlign: TextAlign.center,
      ),
    );

    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        child: Column(
          children: [
            _Header(
              state: _embState,
              quietMode: _quietMode,
              onQuietToggle: () => _toggleQuietMode(!_quietMode),
              onBackground: isSummoned ? _background : null,
            ),
            if (isSummoned) ...[
              // ── Summoned: compact orb at top, chat below ─────────────────
              AuroraOrb(
                state:     orbState,
                pulse:     _pulseAnim,
                axisState: _axisState,
                size:      116,   // height ≈ 116 × 1.9 = 220 dp
              ),
              const SizedBox(height: 6),
              statusWidget,
              if (!_screenObserverReady) ...[
                const SizedBox(height: 4),
                TextButton(
                  onPressed: _requestScreenObserver,
                  child: const Text('Enable screen observer'),
                ),
              ],
              const SizedBox(height: 4),
              Expanded(
                child: ListView.builder(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: _msgs.length,
                  itemBuilder: (_, i) => _ChatBubble(msg: _msgs[i]),
                ),
              ),
              _InputBar(controller: _textCtrl, onSend: _sendMessage),
            ] else ...[
              // ── Idle: orb fills all available space ──────────────────────
              // Tap anywhere on the avatar to summon Aurora.
              Expanded(
                child: LayoutBuilder(
                  builder: (_, constraints) {
                    final h = constraints.maxHeight;
                    return GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTap: _summon,
                      child: Stack(
                        children: [
                          AuroraOrb(
                            state:     orbState,
                            pulse:     _pulseAnim,
                            axisState: _axisState,
                            size:      h * 0.48,
                            height:    h,
                          ),
                          // Status / partial-speech text floats near the bottom
                          Positioned(
                            bottom: 28,
                            left: 0,
                            right: 0,
                            child: Center(child: statusWidget),
                          ),
                          if (!_screenObserverReady)
                            Positioned(
                              bottom: 6,
                              left: 0,
                              right: 0,
                              child: Center(
                                child: TextButton(
                                  onPressed: _requestScreenObserver,
                                  child: const Text('Enable screen observer'),
                                ),
                              ),
                            ),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _pulseCtrl.dispose();
    _textCtrl.dispose();
    _scrollCtrl.dispose();
    _bridgeSub?.cancel();
    _convTimer?.cancel();
    AuroraBridge.stopListening();
    AuroraBridge.stopSpeaking();
    super.dispose();
  }
}

// ── Sub-widgets ─────────────────────────────────────────────────────────……[...]

class _Header extends StatelessWidget {
  final String state;
  final bool quietMode;
  final VoidCallback onQuietToggle;
  final AsyncCallback? onBackground;
  _Header({required this.state, required this.quietMode, required this.onQuietToggle, this.onBackground});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 8, 0),
      child: Row(
        children: [
          const Text('Aurora',
            style: TextStyle(
              color: _purple, fontSize: 22,
              fontWeight: FontWeight.w300, letterSpacing: 3,
            ),
          ),
          const Spacer(),
          IconButton(
            icon: Icon(
              quietMode ? Icons.volume_off_rounded : Icons.volume_up_rounded,
              color: quietMode ? Colors.white38 : Colors.white54,
            ),
            onPressed: onQuietToggle,
            tooltip: quietMode ? 'Quiet mode (tap to unmute)' : 'Quiet mode',
          ),
          if (state == 'SUMMONED')
            IconButton(
              icon: const Icon(Icons.visibility_rounded, color: Colors.white54),
              onPressed: () => AuroraBridge.captureVision(),
              tooltip: 'Capture Vision',
            ),
          if (state == 'SUMMONED' && onBackground != null)
            IconButton(
              icon: const Icon(Icons.keyboard_arrow_down, color: Colors.white54),
              onPressed: onBackground,
              tooltip: 'Background',
            ),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  final ChatMsg msg;
  const _ChatBubble({required this.msg});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: msg.isUser ? const Color(0xFF3A1060) : const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(msg.text,
          style: const TextStyle(color: Colors.white, fontSize: 15, height: 1.4)),
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String> onSend;
  const _InputBar({required this.controller, required this.onSend});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 12, right: 12, top: 8,
        bottom: MediaQuery.of(context).viewInsets.bottom + 12,
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Message Aurora…',
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.35)),
                filled: true,
                fillColor: const Color(0xFF1C1C28),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
              ),
              onSubmitted: onSend,
              textInputAction: TextInputAction.send,
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: () => onSend(controller.text),
            child: Container(
              width: 44, height: 44,
              decoration: const BoxDecoration(color: _purple, shape: BoxShape.circle),
              child: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
            ),
          ),
        ],
      ),
    );
  }
}
