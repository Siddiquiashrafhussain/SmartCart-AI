import 'package:flutter/foundation.dart';

class AppConfig {
  static String? _customBaseUrl;

  /// Default API base URL depending on runtime platform:
  /// - Android Emulator: http://10.0.2.2:8000/api/v1
  /// - Web / Windows Desktop / macOS: http://127.0.0.1:8000/api/v1
  static String get apiBaseUrl {
    if (_customBaseUrl != null && _customBaseUrl!.isNotEmpty) {
      return _customBaseUrl!;
    }
    if (kIsWeb) {
      return 'http://127.0.0.1:8000/api/v1';
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'http://10.0.2.2:8000/api/v1';
      default:
        return 'http://127.0.0.1:8000/api/v1';
    }
  }

  static void setCustomBaseUrl(String url) {
    _customBaseUrl = url.trim();
  }

  static const String appName = 'SmartCart AI';
  static const String tagline = 'Shop Smarter. Verify Instantly. Restock Proactively.';
  static const String defaultUserId = 'shopper_mobile_01';
  static const String defaultCartId = 'CART-MOBILE-01';
}
