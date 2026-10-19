/// SmartCart AI - Scan & Go Barcode Scanner Screen

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:smartcart_mobile/core/theme.dart';
import 'package:smartcart_mobile/services/cart_controller.dart';
import 'package:smartcart_mobile/widgets/dev_barcode_sheet.dart';

class ScannerScreen extends StatefulWidget {
  final CartController cartController;

  const ScannerScreen({
    super.key,
    required this.cartController,
  });

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  late final MobileScannerController _scannerController;
  bool _isProcessingScan = false;
  DateTime _lastScanTime = DateTime.now().subtract(const Duration(seconds: 5));

  @override
  void initState() {
    super.initState();
    _scannerController = MobileScannerController(
      detectionSpeed: DetectionSpeed.normal,
      facing: CameraFacing.back,
      torchEnabled: false,
    );
  }

  @override
  void dispose() {
    _scannerController.dispose();
    super.dispose();
  }

  Future<void> _handleBarcodeDetected(String rawBarcode) async {
    final barcode = rawBarcode.trim();
    if (barcode.isEmpty) return;

    // Debounce to prevent rapid double-scanning of same item in 2 seconds
    final now = DateTime.now();
    if (now.difference(_lastScanTime).inMilliseconds < 1800) {
      return;
    }
    _lastScanTime = now;

    if (_isProcessingScan) return;
    setState(() => _isProcessingScan = true);

    final success = await widget.cartController.scanBarcode(barcode);
    if (!mounted) return;

    setState(() => _isProcessingScan = false);

    if (success) {
      _showScanSuccessFeedback(barcode);
    } else {
      _showScanErrorFeedback(barcode);
    }
  }

  void _showScanSuccessFeedback(String barcode) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.white, size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Item Added to Cart!', style: TextStyle(fontWeight: FontWeight.bold)),
                  Text('Barcode: $barcode', style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
                ],
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.successGreen,
        duration: const Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  void _showScanErrorFeedback(String barcode) {
    final errorMsg = widget.cartController.errorMessage ??
        'Barcode "$barcode" does not exist in store catalogue.';

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        icon: const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 48),
        title: const Text('Unknown Barcode', style: TextStyle(fontWeight: FontWeight.bold)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(errorMsg, style: const TextStyle(fontSize: 14)),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                children: [
                  const Icon(Icons.qr_code, size: 16, color: AppTheme.textMuted),
                  const SizedBox(width: 6),
                  Text(
                    'Scanned: $barcode',
                    style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Dismiss'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              _openDevBarcodePicker();
            },
            child: const Text('Pick Known Product'),
          ),
        ],
      ),
    );
  }

  void _openDevBarcodePicker() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DevBarcodeSheet(
        onBarcodeSelected: (barcode) {
          _handleBarcodeDetected(barcode);
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Scan & Go'),
        backgroundColor: AppTheme.primaryDark,
        actions: [
          // Torch toggle
          IconButton(
            icon: const Icon(Icons.flash_on),
            tooltip: 'Toggle Flashlight',
            onPressed: () => _scannerController.toggleTorch(),
          ),
          // Camera switch
          IconButton(
            icon: const Icon(Icons.cameraswitch_outlined),
            tooltip: 'Switch Camera',
            onPressed: () => _scannerController.switchCamera(),
          ),
        ],
      ),
      body: Stack(
        children: [
          // Camera Stream / Error Fallback
          MobileScanner(
            controller: _scannerController,
            onDetect: (capture) {
              final barcodes = capture.barcodes;
              for (final b in barcodes) {
                if (b.rawValue != null) {
                  _handleBarcodeDetected(b.rawValue!);
                  break;
                }
              }
            },
            errorBuilder: (context, error) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.08),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.videocam_off_outlined, size: 54, color: Colors.white70),
                      ),
                      const SizedBox(height: 16),
                      const Text(
                        'Physical Camera Unavailable',
                        style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        kIsWeb || defaultTargetPlatform == TargetPlatform.windows
                            ? 'Running on ${defaultTargetPlatform.name.toUpperCase()} environment.\nUse the Development Barcode Runner below to simulate retail scanning.'
                            : 'Camera hardware could not be initialized.\nPlease grant camera permissions or use the test runner.',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white60, fontSize: 13),
                      ),
                      const SizedBox(height: 20),
                      ElevatedButton.icon(
                        onPressed: _openDevBarcodePicker,
                        icon: const Icon(Icons.qr_code_scanner),
                        label: const Text('Open Test Barcode Picker'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.accentCyan,
                          foregroundColor: AppTheme.primaryDark,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),

          // Viewfinder reticle overlay
          _buildViewfinderOverlay(),

          // Processing Indicator
          if (_isProcessingScan)
            Container(
              color: Colors.black45,
              child: const Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: AppTheme.accentCyan),
                    SizedBox(height: 12),
                    Text(
                      'Looking up product in catalogue...',
                      style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
            ),

          // Bottom Control Panel with Dev Barcode Runner
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: _buildBottomBar(),
          ),
        ],
      ),
    );
  }

  Widget _buildViewfinderOverlay() {
    return IgnorePointer(
      child: Center(
        child: Container(
          width: 270,
          height: 270,
          decoration: BoxDecoration(
            border: Border.all(color: AppTheme.accentCyan, width: 2.5),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [
              BoxShadow(
                color: AppTheme.accentCyan.withOpacity(0.2),
                spreadRadius: 4,
                blurRadius: 16,
              ),
            ],
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Top corner brackets
              Padding(
                padding: const EdgeInsets.all(8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _corner(true, true),
                    _corner(true, false),
                  ],
                ),
              ),
              // Center instruction
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'Align barcode within frame',
                  style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ),
              // Bottom corner brackets
              Padding(
                padding: const EdgeInsets.all(8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _corner(false, true),
                    _corner(false, false),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _corner(bool top, bool left) {
    return Container(
      width: 18,
      height: 18,
      decoration: BoxDecoration(
        border: Border(
          top: top ? const BorderSide(color: Colors.white, width: 3) : BorderSide.none,
          bottom: !top ? const BorderSide(color: Colors.white, width: 3) : BorderSide.none,
          left: left ? const BorderSide(color: Colors.white, width: 3) : BorderSide.none,
          right: !left ? const BorderSide(color: Colors.white, width: 3) : BorderSide.none,
        ),
      ),
    );
  }

  Widget _buildBottomBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.primaryDark.withOpacity(0.92),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.info_outline, color: AppTheme.accentCyan, size: 20),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'Physical scanning or Dev Simulator available.',
                  style: TextStyle(color: Colors.white, fontSize: 13),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _openDevBarcodePicker,
              icon: const Icon(Icons.tune),
              label: const Text('Development Barcode Picker / Input'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryBlue,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
