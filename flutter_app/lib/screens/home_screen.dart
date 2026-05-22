import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';

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
  String _embState = 'DORMANT'; // DORMANT | BACKGROUND | SUMMONED

  // ── Orb animation ───────────────────────────────────────────────────────
  late AnimationController _pulseCtrl;
  late Animation<double>   _pulseAnim;

  // ── Chat ────────────────────────────────────────────────────────────────
  final List<ChatMsg>       _msgs      = [];
  final TextEditingController _textCtrl = TextEditingController();
  final ScrollController    _scrollCtrl = ScrollController();

  // ── AI state ────────────────────────────────────────────────────────────
  bool   _aiReady   = false;
  String _statusTxt = 'Starting Aurora…';

  // ── STT ─────────────────────────────────────────────────────────────────
  final SpeechToText _stt         = SpeechToText();
  bool               _sttOk       = false;
  bool               _listening   = false;
  String             _partialText = '';

  // ── TTS ─────────────────────────────────────────────────────────────────
  final FlutterTts _tts      = FlutterTts();
  bool             _speaking = false;

  // ── Conversation window after wake-word ─────────────────────────────────
  static const _convSec = 30;
  Timer?  _convTimer;
  bool    _inConversation = false;

  // ── Bridge events ────────────────────────────────────────────────────────
  StreamSubscription? _bridgeSub;

  // ── Overlay ──────────────────────────────────────────────────────────────
  StreamSubscription? _overlaySub;

  // ─────────────────────────────────────────────────────────────────────────

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
    await _initTts();
    await _requestPermissions();
    _listenBridgeEvents();
    _listenOverlayTaps();
    setState(() => _embState = 'BACKGROUND');
  }

  Future<void> _initTts() async {
    await _tts.setLanguage('en-US');
    await _tts.setSpeechRate(0.48);
    await _tts.setVolume(1.0);
    _tts.setCompletionHandler(() {
      if (mounted) setState(() => _speaking = false);
      if (_embState == 'SUMMONED') _startListening();
    });
  }

  Future<void> _requestPermissions() async {
    await [Permission.microphone, Permission.notification].request();
    _sttOk = await _stt.initialize(
      onStatus: _onSttStatus,
      onError:  (e) => debugPrint('STT error: $e'),
    );
    if (_sttOk && _embState != 'DORMANT') _startListening();
  }

  void _listenBridgeEvents() {
    _bridgeSub = AuroraBridge.events.listen((event) {
      final type = event['type'] as String? ?? '';
      final text = event['text'] as String? ?? '';
      switch (type) {
        case 'ready':
          setState(() {
            _aiReady   = true;
            _statusTxt = 'Listening…';
          });
          _speak("Aurora is online.");
        case 'response':
          // handled synchronously in _sendMessage; ignore duplicate here
          break;
        case 'error':
          setState(() => _statusTxt = 'Error: $text');
      }
    });
  }

  void _listenOverlayTaps() {
    _overlaySub = FlutterOverlayWindow.overlayListener.listen((data) {
      if (data == 'tapped') _summon();
    });
  }

  // ── Embodiment transitions ────────────────────────────────────────────────

  void _summon() {
    if (_embState == 'SUMMONED') return;
    setState(() => _embState = 'SUMMONED');
    AuroraBridge.setState('SUMMONED');
    FlutterOverlayWindow.closeOverlay();
    _startConversationWindow();
  }

  void _background() {
    _convTimer?.cancel();
    _inConversation = false;
    setState(() {
      _embState  = 'BACKGROUND';
      _statusTxt = 'Listening for "Aurora"…';
    });
    AuroraBridge.setState('BACKGROUND');
    _showOverlay();
  }

  Future<void> _showOverlay() async {
    try {
      final hasPerm = await AuroraBridge.hasOverlayPermission();
      if (!hasPerm) {
        await AuroraBridge.requestOverlayPermission();
        return;
      }
      await FlutterOverlayWindow.showOverlay(
        height: 80,
        width: 80,
        flag: OverlayFlag.defaultFlag,
        alignment: OverlayAlignment.bottomLeft,
        positionGravity: PositionGravity.auto,
      );
    } catch (e) {
      debugPrint('showOverlay: $e');
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

  // ── STT ──────────────────────────────────────────────────────────────────

  void _onSttStatus(String status) {
    if (status == 'done' || status == 'notListening') {
      if (mounted) setState(() => _listening = false);
      // Restart if we're still in an active state and not speaking
      if (!_speaking && (_embState != 'DORMANT')) {
        Future.delayed(const Duration(milliseconds: 400), _startListening);
      }
    }
  }

  void _startListening() {
    if (!_sttOk || _listening || _speaking || _embState == 'DORMANT') return;
    setState(() {
      _listening   = true;
      _partialText = '';
    });
    _stt.listen(
      onResult: _onSttResult,
      listenFor: Duration(seconds: _inConversation ? 20 : 45),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      cancelOnError: false,
      listenMode: ListenMode.confirmation,
    );
  }

  void _onSttResult(result) {
    final words = result.recognizedWords as String;
    setState(() => _partialText = words);

    if (!result.finalResult) return;
    setState(() {
      _listening   = false;
      _partialText = '';
    });

    final lower = words.toLowerCase().trim();
    if (lower.isEmpty) return;

    if (_inConversation) {
      // Inside conversation window — send directly
      _resetConversationWindow();
      _sendMessage(words);
    } else {
      // Outside — check for wake word
      final idx = lower.indexOf('aurora');
      if (idx == -1) return;
      final after = words.substring(idx + 6).trim();
      _summon();
      if (after.isNotEmpty) {
        Future.delayed(const Duration(milliseconds: 300), () => _sendMessage(after));
      } else {
        _speak("Yes?");
      }
    }
  }

  // ── TTS ───────────────────────────────────────────────────────────────────

  Future<void> _speak(String text) async {
    if (text.isEmpty) return;
    _stt.cancel();
    setState(() {
      _speaking = true;
      _listening = false;
    });
    await _tts.speak(text);
  }

  // ── Message send ─────────────────────────────────────────────────────────

  Future<void> _sendMessage(String text) async {
    text = text.trim();
    if (text.isEmpty) return;
    _textCtrl.clear();
    _stt.cancel();

    setState(() {
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

  // ── App lifecycle ─────────────────────────────────────────────────────────

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused && _embState != 'DORMANT') {
      _background();
    } else if (state == AppLifecycleState.resumed) {
      FlutterOverlayWindow.closeOverlay();
      if (_embState == 'BACKGROUND') _startListening();
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────

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
            // ── Header ──────────────────────────────────────────────────
            _Header(
              state: _embState,
              onBackground: isSummoned ? _background : null,
            ),
            // ── Orb + status ─────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Column(
                children: [
                  AuroraOrb(
                    state:  orbState,
                    pulse:  _pulseAnim,
                    size:   isSummoned ? 100 : 140,
                    onTap:  isSummoned ? null : _summon,
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
                            ? FontStyle.italic
                            : FontStyle.normal,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
            // ── Chat (visible when summoned) ─────────────────────────────
            if (isSummoned) ...[
              Expanded(
                child: ListView.builder(
                  controller: _scrollCtrl,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: _msgs.length,
                  itemBuilder: (_, i) => _ChatBubble(msg: _msgs[i]),
                ),
              ),
              _InputBar(
                controller: _textCtrl,
                onSend: _sendMessage,
              ),
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
    _overlaySub?.cancel();
    _convTimer?.cancel();
    _stt.cancel();
    _tts.stop();
    super.dispose();
  }
}

// ── Sub-widgets ───────────────────────────────────────────────────────────────

class _Header extends StatelessWidget {
  final String state;
  final VoidCallback? onBackground;
  const _Header({required this.state, this.onBackground});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 8, 0),
      child: Row(
        children: [
          const Text(
            'Aurora',
            style: TextStyle(
              color: _purple,
              fontSize: 22,
              fontWeight: FontWeight.w300,
              letterSpacing: 3,
            ),
          ),
          const Spacer(),
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
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: msg.isUser
              ? const Color(0xFF3A1060)
              : const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Text(
          msg.text,
          style: const TextStyle(color: Colors.white, fontSize: 15, height: 1.4),
        ),
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
        left: 12, right: 12,
        bottom: MediaQuery.of(context).viewInsets.bottom + 12,
        top: 8,
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
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
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
              width: 44,
              height: 44,
              decoration: const BoxDecoration(
                color: _purple,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
            ),
          ),
        ],
      ),
    );
  }
}
