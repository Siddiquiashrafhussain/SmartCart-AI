/// SmartCart AI - Main Navigation Shell & Settings

import 'package:flutter/material.dart';
import 'package:smartcart_mobile/core/config.dart';
import 'package:smartcart_mobile/core/theme.dart';
import 'package:smartcart_mobile/screens/catalog_screen.dart';
import 'package:smartcart_mobile/screens/scanner_screen.dart';
import 'package:smartcart_mobile/screens/cart_screen.dart';
import 'package:smartcart_mobile/services/api_service.dart';
import 'package:smartcart_mobile/services/cart_controller.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _currentIndex = 1; // Default to Scanner tab for Scan & Go experience
  late final ApiService _apiService;
  late final CartController _cartController;

  @override
  void initState() {
    super.initState();
    _apiService = ApiService();
    _cartController = CartController(apiService: _apiService);
    _cartController.initialize();
  }

  @override
  void dispose() {
    _cartController.dispose();
    super.dispose();
  }

  void _openSettingsDialog() {
    final controller = TextEditingController(text: AppConfig.apiBaseUrl);

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.settings, color: AppTheme.primaryBlue),
            SizedBox(width: 8),
            Text('API Configuration'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Backend API Base URL:',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                hintText: 'http://127.0.0.1:8000/api/v1',
                isDense: true,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Presets:',
              style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
            ),
            Wrap(
              spacing: 6,
              children: [
                ActionChip(
                  label: const Text('Localhost (Desktop/Web)', style: TextStyle(fontSize: 11)),
                  onPressed: () => controller.text = 'http://127.0.0.1:8000/api/v1',
                ),
                ActionChip(
                  label: const Text('Android 10.0.2.2', style: TextStyle(fontSize: 11)),
                  onPressed: () => controller.text = 'http://10.0.2.2:8000/api/v1',
                ),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              AppConfig.setCustomBaseUrl(controller.text);
              Navigator.of(ctx).pop();
              _cartController.initialize();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('Updated Base URL to: ${AppConfig.apiBaseUrl}'),
                  backgroundColor: AppTheme.primaryBlue,
                ),
              );
            },
            child: const Text('Save & Reconnect'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: _cartController,
      builder: (context, _) {
        final totalItems = _cartController.totalQuantity;
        final isConnected = _cartController.isBackendConnected;

        final screens = [
          CatalogScreen(
            cartController: _cartController,
            apiService: _apiService,
          ),
          ScannerScreen(
            cartController: _cartController,
          ),
          CartScreen(
            cartController: _cartController,
            onStartScanning: () {
              setState(() => _currentIndex = 1);
            },
          ),
        ];

        return Scaffold(
          appBar: AppBar(
            backgroundColor: AppTheme.primaryDark,
            elevation: 0,
            title: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: AppTheme.accentCyan.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(
                    Icons.shopping_cart_checkout,
                    color: AppTheme.accentCyan,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 10),
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'SmartCart AI',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    Text(
                      'Scan & Go',
                      style: TextStyle(
                        fontSize: 11,
                        color: AppTheme.accentCyan,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            actions: [
              // Online / Offline Status Pill
              Container(
                margin: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: isConnected
                      ? AppTheme.successGreen.withOpacity(0.2)
                      : AppTheme.warningOrange.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isConnected ? AppTheme.successGreen : AppTheme.warningOrange,
                    width: 1,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isConnected ? AppTheme.successGreen : AppTheme.warningOrange,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      isConnected ? 'Online' : 'Offline',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: isConnected ? AppTheme.successGreen : AppTheme.warningOrange,
                      ),
                    ),
                  ],
                ),
              ),

              // Settings button
              IconButton(
                icon: const Icon(Icons.settings_outlined, color: Colors.white70),
                tooltip: 'Network & API Settings',
                onPressed: _openSettingsDialog,
              ),
            ],
          ),
          body: IndexedStack(
            index: _currentIndex,
            children: screens,
          ),
          bottomNavigationBar: BottomNavigationBar(
            currentIndex: _currentIndex,
            onTap: (index) => setState(() => _currentIndex = index),
            items: [
              const BottomNavigationBarItem(
                icon: Icon(Icons.storefront_outlined),
                activeIcon: Icon(Icons.storefront),
                label: 'Catalogue',
              ),
              const BottomNavigationBarItem(
                icon: Icon(Icons.qr_code_scanner_outlined),
                activeIcon: Icon(Icons.qr_code_scanner),
                label: 'Scan & Go',
              ),
              BottomNavigationBarItem(
                icon: Badge(
                  isLabelVisible: totalItems > 0,
                  label: Text('$totalItems'),
                  backgroundColor: AppTheme.primaryBlue,
                  child: const Icon(Icons.shopping_cart_outlined),
                ),
                activeIcon: Badge(
                  isLabelVisible: totalItems > 0,
                  label: Text('$totalItems'),
                  backgroundColor: AppTheme.primaryBlue,
                  child: const Icon(Icons.shopping_cart),
                ),
                label: 'Cart',
              ),
            ],
          ),
        );
      },
    );
  }
}
