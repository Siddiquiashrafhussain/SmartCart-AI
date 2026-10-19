/// SmartCart AI - Cart Item Model

import 'package:smartcart_mobile/models/product.dart';

class CartItem {
  final int id;
  final int productId;
  final Product product;
  int quantity;
  final double unitPrice;
  double totalPrice;

  CartItem({
    required this.id,
    required this.productId,
    required this.product,
    required this.quantity,
    required this.unitPrice,
    required this.totalPrice,
  });

  factory CartItem.fromJson(Map<String, dynamic> json) {
    final qty = json['quantity'] as int? ?? 1;
    final unitP = (json['unit_price'] as num?)?.toDouble() ?? 0.0;
    final totalP = (json['total_price'] as num?)?.toDouble() ?? (qty * unitP);

    return CartItem(
      id: json['id'] as int? ?? 0,
      productId: json['product_id'] as int? ?? 0,
      product: Product.fromJson(json['product'] as Map<String, dynamic>),
      quantity: qty,
      unitPrice: unitP,
      totalPrice: double.parse(totalP.toStringAsFixed(2)),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'product_id': productId,
    'product': product.toJson(),
    'quantity': quantity,
    'unit_price': unitPrice,
    'total_price': totalPrice,
  };

  CartItem copyWith({
    int? id,
    int? productId,
    Product? product,
    int? quantity,
    double? unitPrice,
    double? totalPrice,
  }) {
    final newQty = quantity ?? this.quantity;
    final newUnit = unitPrice ?? this.unitPrice;
    return CartItem(
      id: id ?? this.id,
      productId: productId ?? this.productId,
      product: product ?? this.product,
      quantity: newQty,
      unitPrice: newUnit,
      totalPrice: totalPrice ?? double.parse((newQty * newUnit).toStringAsFixed(2)),
    );
  }

  String get formattedUnitPrice => '\$${unitPrice.toStringAsFixed(2)}';
  String get formattedTotalPrice => '\$${totalPrice.toStringAsFixed(2)}';
}
