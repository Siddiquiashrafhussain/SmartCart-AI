/// SmartCart AI - Virtual Cart Screen

import 'package:flutter/material.dart';
import 'package:smartcart_mobile/core/theme.dart';
import 'package:smartcart_mobile/services/cart_controller.dart';
import 'package:smartcart_mobile/widgets/cart_item_tile.dart';

class CartScreen extends StatelessWidget {
  final CartController cartController;
  final VoidCallback onStartScanning;

  const CartScreen({
    super.key,
    required this.cartController,
    required this.onStartScanning,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: cartController,
      builder: (context, _) {
        final session = cartController.session;
        final items = cartController.items;
        final isEmpty = cartController.isEmpty;

        return Scaffold(
          appBar: AppBar(
            title: const Text('Virtual Shopping Cart'),
            actions: [
              if (!isEmpty)
                TextButton.icon(
                  onPressed: () => _confirmClearCart(context),
                  icon: const Icon(Icons.delete_sweep, color: Colors.white70, size: 18),
                  label: const Text('Clear', style: TextStyle(color: Colors.white70)),
                ),
            ],
          ),
          body: Stack(
            children: [
              Column(
                children: [
                  // Session status banner
                  _buildSessionHeader(context, session),

                  // Main content: Empty state or Item List + Summary
                  Expanded(
                    child: isEmpty
                        ? _buildEmptyState(context)
                        : Column(
                            children: [
                              // Item List
                              Expanded(
                                child: ListView.builder(
                                  padding: const EdgeInsets.symmetric(vertical: 8),
                                  itemCount: items.length,
                                  itemBuilder: (context, index) {
                                    final item = items[index];
                                    return CartItemTile(
                                      item: item,
                                      onQuantityChanged: (newQty) {
                                        cartController.updateQuantity(item.id, newQty);
                                      },
                                      onRemove: () {
                                        cartController.removeItem(item.id);
                                      },
                                    );
                                  },
                                ),
                              ),

                              // Bottom Order Summary Card
                              _buildSummaryCard(context),
                            ],
                          ),
                  ),
                ],
              ),

              // Loading overlay during API mutations
              if (cartController.isLoading)
                Container(
                  color: Colors.black26,
                  child: const Center(
                    child: Card(
                      child: Padding(
                        padding: EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            CircularProgressIndicator(strokeWidth: 3),
                            SizedBox(width: 16),
                            Text('Syncing with cart...'),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSessionHeader(BuildContext context, dynamic session) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      color: const Color(0xFFF1F5F9),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Icon(
                cartController.isBackendConnected ? Icons.cloud_done : Icons.cloud_off,
                size: 16,
                color: cartController.isBackendConnected ? AppTheme.successGreen : AppTheme.warningOrange,
              ),
              const SizedBox(width: 6),
              Text(
                session != null
                    ? 'Session #${session.id} • ${session.cartId}'
                    : (cartController.isBackendConnected
                        ? 'Connected to Backend'
                        : 'Offline Preview Mode'),
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textDark,
                ),
              ),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: AppTheme.primaryBlue.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '${cartController.totalQuantity} items',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryBlue,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: AppTheme.primaryBlue.withOpacity(0.06),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.shopping_cart_outlined,
                size: 64,
                color: AppTheme.primaryBlue,
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'Your Virtual Cart is Empty',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppTheme.textDark,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Scan product barcodes in-store or browse the catalog to add items to your cart.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13, color: AppTheme.textMuted),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: onStartScanning,
              icon: const Icon(Icons.qr_code_scanner),
              label: const Text('Start Scanning'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primaryBlue,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryCard(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.08),
            blurRadius: 10,
            offset: const Offset(0, -3),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Subtotal
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Subtotal', style: TextStyle(fontSize: 14, color: AppTheme.textMuted)),
                Text(
                  cartController.formattedSubtotal,
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textDark),
                ),
              ],
            ),
            const SizedBox(height: 6),

            // Estimated Tax
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Estimated Sales Tax (8.25%)', style: TextStyle(fontSize: 13, color: AppTheme.textMuted)),
                Text(
                  cartController.formattedTax,
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500, color: AppTheme.textDark),
                ),
              ],
            ),
            const Divider(height: 18),

            // Grand Total
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Cart Total',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.primaryDark),
                ),
                Text(
                  cartController.formattedGrandTotal,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.primaryDark,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Verified Scan & Go Ready Indicator
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 14),
              decoration: BoxDecoration(
                color: const Color(0xFFF0FDF4),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.successGreen.withOpacity(0.3)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.verified_user_outlined, color: AppTheme.successGreen, size: 20),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'All items synced with SmartCart AI verification engine.',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF166534),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _confirmClearCart(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Clear Shopping Cart?'),
        content: const Text('Are you sure you want to remove all items from your cart?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              cartController.clearCart();
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.errorRed),
            child: const Text('Clear Cart'),
          ),
        ],
      ),
    );
  }
}
