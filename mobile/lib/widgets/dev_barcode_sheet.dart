/// SmartCart AI - Development / Test Barcode Runner
///
/// Designed explicitly for environments where physical camera video capture
/// is unavailable (Windows desktop, Chrome, emulator without camera, headless CI).
/// Allows testing real barcode lookup, unknown barcode error states, and cart updates.

import 'package:flutter/material.dart';
import 'package:smartcart_mobile/core/theme.dart';

class DevBarcodeSheet extends StatefulWidget {
  final ValueChanged<String> onBarcodeSelected;

  const DevBarcodeSheet({
    super.key,
    required this.onBarcodeSelected,
  });

  @override
  State<DevBarcodeSheet> createState() => _DevBarcodeSheetState();
}

class _DevBarcodeSheetState extends State<DevBarcodeSheet> {
  final TextEditingController _customBarcodeController = TextEditingController();

  static const List<Map<String, String>> _seededProducts = [
    {
      'barcode': '8901030018241',
      'name': 'Organic Whole Wheat Cereal (500g)',
      'price': '\$4.99',
      'category': 'Breakfast & Cereal',
    },
    {
      'barcode': '8901030029312',
      'name': 'Whole Milk Gallon (3.78L)',
      'price': '\$3.79',
      'category': 'Dairy & Refrigerated',
    },
    {
      'barcode': '8901030034567',
      'name': 'Artisan Sourdough Bread (400g)',
      'price': '\$4.25',
      'category': 'Bakery',
    },
    {
      'barcode': '8901030045678',
      'name': 'Sparkling Mineral Water (1L)',
      'price': '\$1.89',
      'category': 'Beverages',
    },
    {
      'barcode': '8901030056789',
      'name': 'Classic Potato Chips (200g)',
      'price': '\$2.49',
      'category': 'Snacks',
    },
    {
      'barcode': '8901030067890',
      'name': 'Double Chocolate Cookies (300g)',
      'price': '\$3.99',
      'category': 'Snacks',
    },
    {
      'barcode': '8901030078901',
      'name': 'Organic Greek Yogurt (500g)',
      'price': '\$4.50',
      'category': 'Dairy & Refrigerated',
    },
    {
      'barcode': '8901030089012',
      'name': 'Extra Virgin Olive Oil (750ml)',
      'price': '\$9.99',
      'category': 'Pantry & Staples',
    },
  ];

  @override
  void dispose() {
    _customBarcodeController.dispose();
    super.dispose();
  }

  void _submitCustomBarcode() {
    final barcode = _customBarcodeController.text.trim();
    if (barcode.isNotEmpty) {
      Navigator.of(context).pop();
      widget.onBarcodeSelected(barcode);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        top: 16,
        left: 16,
        right: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Drag handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: AppTheme.warningOrange.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'DEVELOPMENT ONLY',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.warningOrange,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'Quick Barcode Scanner & Tester',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textDark),
          ),
          const SizedBox(height: 4),
          const Text(
            'Use this test panel when physical camera hardware is unavailable to simulate real barcode lookup and cart additions.',
            style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 14),

          // Manual Input Form
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _customBarcodeController,
                  decoration: InputDecoration(
                    hintText: 'Enter barcode (e.g. 8901030018241)',
                    isDense: true,
                    prefixIcon: const Icon(Icons.keyboard_outlined, size: 18),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  onSubmitted: (_) => _submitCustomBarcode(),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton(
                onPressed: _submitCustomBarcode,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                child: const Text('Lookup'),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Test Error Case Button
          OutlinedButton.icon(
            onPressed: () {
              Navigator.of(context).pop();
              widget.onBarcodeSelected('9999999999999_UNKNOWN');
            },
            icon: const Icon(Icons.error_outline, size: 16, color: AppTheme.errorRed),
            label: const Text(
              'Test Invalid / Unknown Barcode (Trigger 404 Error State)',
              style: TextStyle(fontSize: 12, color: AppTheme.errorRed, fontWeight: FontWeight.w600),
            ),
            style: OutlinedButton.styleFrom(
              side: BorderSide(color: AppTheme.errorRed.withOpacity(0.5)),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
            ),
          ),
          const SizedBox(height: 12),

          const Text(
            'Or select a seeded catalog item to scan:',
            style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppTheme.textDark),
          ),
          const SizedBox(height: 8),

          // Seeded list
          Flexible(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 260),
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: _seededProducts.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final item = _seededProducts[index];
                  return ListTile(
                    dense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    leading: const CircleAvatar(
                      radius: 16,
                      backgroundColor: Color(0xFFF1F5F9),
                      child: Icon(Icons.qr_code, size: 16, color: AppTheme.primaryBlue),
                    ),
                    title: Text(
                      item['name']!,
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      'Barcode: ${item['barcode']} • ${item['category']}',
                      style: const TextStyle(fontSize: 11, fontFamily: 'monospace'),
                    ),
                    trailing: Text(
                      item['price']!,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryDark,
                      ),
                    ),
                    onTap: () {
                      Navigator.of(context).pop();
                      widget.onBarcodeSelected(item['barcode']!);
                    },
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
