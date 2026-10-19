/// SmartCart AI - Product Card Widget

import 'package:flutter/material.dart';
import 'package:smartcart_mobile/core/theme.dart';
import 'package:smartcart_mobile/models/product.dart';

class ProductCard extends StatelessWidget {
  final Product product;
  final VoidCallback onAddToCart;

  const ProductCard({
    super.key,
    required this.product,
    required this.onAddToCart,
  });

  @override
  Widget build(BuildContext context) {
    final inv = product.inventory;
    final isStockout = inv?.isStockout ?? false;
    final isLowStock = inv?.isLowStock ?? false;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
      elevation: 1.5,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: isStockout ? AppTheme.errorRed.withOpacity(0.3) : const Color(0xFFE2E8F0),
          width: 1,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Left Category / Product Icon Avatar
            Container(
              width: 58,
              height: 58,
              decoration: BoxDecoration(
                color: AppTheme.primaryBlue.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Center(
                child: Icon(
                  _getCategoryIcon(product.category),
                  color: AppTheme.primaryBlue,
                  size: 28,
                ),
              ),
            ),
            const SizedBox(width: 14),

            // Middle: Name, SKU, Category, Weight, Stock Pill
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Category tag
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF1F5F9),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      product.category.toUpperCase(),
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.textMuted,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),

                  // Product Name
                  Text(
                    product.name,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.textDark,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),

                  // Barcode & Weight
                  Row(
                    children: [
                      Icon(Icons.qr_code_2, size: 13, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Text(
                        product.barcode,
                        style: TextStyle(
                          fontSize: 11,
                          fontFamily: 'monospace',
                          color: Colors.grey.shade600,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Icon(Icons.scale_outlined, size: 13, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Text(
                        product.formattedWeight,
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),

                  // Stock Status Badge
                  if (isStockout)
                    _buildStockBadge('OUT OF STOCK', AppTheme.errorRed)
                  else if (isLowStock)
                    _buildStockBadge('LOW STOCK (${inv!.totalStoreStock} left)', AppTheme.warningOrange)
                  else
                    _buildStockBadge('IN STOCK (${inv?.totalStoreStock ?? "Available"})', AppTheme.successGreen),
                ],
              ),
            ),
            const SizedBox(width: 10),

            // Right: Price & Add to Cart Button
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  product.formattedPrice,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.primaryDark,
                  ),
                ),
                const SizedBox(height: 8),
                ElevatedButton(
                  onPressed: isStockout ? null : onAddToCart,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: Colors.grey.shade300,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    minimumSize: const Size(36, 36),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.add_shopping_cart, size: 16),
                      SizedBox(width: 4),
                      Text('Add', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStockBadge(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 7,
          height: 7,
          decoration: BoxDecoration(shape: BoxShape.circle, color: color),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      ],
    );
  }

  IconData _getCategoryIcon(String category) {
    switch (category.toLowerCase()) {
      case 'breakfast & cereal':
        return Icons.breakfast_dining;
      case 'dairy & refrigerated':
      case 'dairy':
        return Icons.egg_alt_outlined;
      case 'bakery':
        return Icons.bakery_dining;
      case 'beverages':
        return Icons.local_drink;
      case 'snacks':
        return Icons.cookie_outlined;
      case 'pantry & staples':
      case 'pantry':
        return Icons.kitchen;
      default:
        return Icons.shopping_bag_outlined;
    }
  }
}
