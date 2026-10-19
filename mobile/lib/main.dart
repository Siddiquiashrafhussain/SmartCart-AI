/// SmartCart AI - Flutter Mobile Application Entry Point

import 'package:flutter/material.dart';
import 'package:smartcart_mobile/core/config.dart';
import 'package:smartcart_mobile/core/theme.dart';
import 'package:smartcart_mobile/screens/home_shell.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const SmartCartApp());
}

class SmartCartApp extends StatelessWidget {
  const SmartCartApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConfig.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const HomeShell(),
    );
  }
}
