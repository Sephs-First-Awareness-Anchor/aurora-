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

  // ── STT / TTS state ─────────────────────────────────────────────────────
  bool   _listening   = false;
  bool   _speaking    = false;
  String _partialText = '';

  // ── Conversation window ──────────────────────────────────────────────────
  static const _convSec = 30;
  Timer? _convTimer;
  bool   _inConversation = false;

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
            if (_embState != 'DORMANT') _startListening();
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
        default: // aurora service events
          switch (type) {
            case 'ready':
              if (mounted) {
                setState(() { _aiReady = true; _statusTxt = 'Listening…'; });
              }
              _speak('Aurora is online.');
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

  void _processRecognizedText(String words) {
    final lower = words.toLowerCase().trim();
    if (lower.isEmpty) {
      if (!_speaking) _startListening();
      return;
    }

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
    _speak(reply);
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

    return Scaffold(
      backgroundColor: _bg,
      body: SafeArea(
        child: Column(
          children: [
            _Header(state: _embState, onBackground: isSummoned ? _background : null),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Column(
                children: [
                  AuroraOrb(
                    state: orbState,
                    pulse: _pulseAnim,
                    size:  isSummoned ? 100 : 140,
                    onTap: isSummoned ? null : _summon,
                  ),
                  const SizedBox(height: 12),
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: Text(
                      _partialText.isNotEmpty ? _partialText : _statusTxt,
                      key: ValueKey(_partialText.isNotEmpty),
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.6),
                        fontSize: 13,
                        fontStyle: _partialText.isNotEmpty
                            ? FontStyle.italic : FontStyle.normal,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
            if (isSummoned) ...[
              Expanded(
                child: ListView.builder(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: _msgs.length,
                  itemBuilder: (_, i) => _ChatBubble(msg: _msgs[i]),
                ),
              ),
              _InputBar(controller: _textCtrl, onSend: _sendMessage),
            ] else
              const Spacer(),
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
  final AsyncCallback? onBackground;
  const _Header({required this.state, this.onBackground});

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
