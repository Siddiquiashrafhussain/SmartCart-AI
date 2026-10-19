/// SmartCart AI - Shopping Session Model

import 'package:smartcart_mobile/models/cart_item.dart';

class ShoppingSession {
  final int id;
  final String userId;
  final String cartId;
  final String status;
  final DateTime startedAt;
  final DateTime? completedAt;
  final List<CartItem> items;
  final int totalItems;
  final double subtotal;

  ShoppingSession({
    required this.id,
    required this.userId,
    required this.cartId,
    required this.status,
    required this.startedAt,
    this.completedAt,
    required this.items,
    required this.totalItems,
    required this.subtotal,
  });

  factory ShoppingSession.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? [];
    final itemsList = rawItems
        .map((item) => CartItem.fromJson(item as Map<String, dynamic>))
        .toList();

    return ShoppingSession(
      id: json['id'] as int? ?? 0,
      userId: json['user_id'] as String? ?? '',
      cartId: json['cart_id'] as String? ?? '',
      status: json['status'] as String? ?? 'ACTIVE',
      startedAt: DateTime.tryParse(json['started_at'] as String? ?? '') ?? DateTime.now(),
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      items: itemsList,
      totalItems: json['total_items'] as int? ?? itemsList.fold(0, (sum, i) => sum + i.quantity),
      subtotal: (json['subtotal'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'cart_id': cartId,
    'status': status,
    'started_at': startedAt.toIso8601String(),
    'completed_at': completedAt?.toIso8601String(),
    'items': items.map((i) => i.toJson()).toList(),
    'total_items': totalItems,
    'subtotal': subtotal,
  };

  /// Estimated Tax (e.g. 8.25% standard retail sales tax)
  double get estimatedTax => double.parse((subtotal * 0.0825).toStringAsFixed(2));

  /// Grand Total including estimated tax
  double get grandTotal => double.parse((subtotal + estimatedTax).toStringAsFixed(2));

  String get formattedSubtotal => '\$${subtotal.toStringAsFixed(2)}';
  String get formattedTax => '\$${estimatedTax.toStringAsFixed(2)}';
  String get formattedGrandTotal => '\$${grandTotal.toStringAsFixed(2)}';
}
