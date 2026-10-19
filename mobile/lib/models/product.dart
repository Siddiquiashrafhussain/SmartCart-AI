/// SmartCart AI - Product Model

class ProductInventory {
  final int id;
  final int totalStoreStock;
  final int estimatedVisibleStock;
  final int safetyThreshold;
  final bool isLowStock;
  final bool isStockout;

  ProductInventory({
    required this.id,
    required this.totalStoreStock,
    required this.estimatedVisibleStock,
    required this.safetyThreshold,
    required this.isLowStock,
    required this.isStockout,
  });

  factory ProductInventory.fromJson(Map<String, dynamic> json) {
    return ProductInventory(
      id: json['id'] as int? ?? 0,
      totalStoreStock: json['total_store_stock'] as int? ?? 0,
      estimatedVisibleStock: json['estimated_visible_stock'] as int? ?? 0,
      safetyThreshold: json['safety_threshold'] as int? ?? 0,
      isLowStock: json['is_low_stock'] as bool? ?? false,
      isStockout: json['is_stockout'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'total_store_stock': totalStoreStock,
    'estimated_visible_stock': estimatedVisibleStock,
    'safety_threshold': safetyThreshold,
    'is_low_stock': isLowStock,
    'is_stockout': isStockout,
  };
}

class Product {
  final int id;
  final String sku;
  final String barcode;
  final String name;
  final String category;
  final double price;
  final double tareWeightG;
  final String? description;
  final String? imageUrl;
  final ProductInventory? inventory;

  Product({
    required this.id,
    required this.sku,
    required this.barcode,
    required this.name,
    required this.category,
    required this.price,
    required this.tareWeightG,
    this.description,
    this.imageUrl,
    this.inventory,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as int? ?? 0,
      sku: json['sku'] as String? ?? '',
      barcode: json['barcode'] as String? ?? '',
      name: json['name'] as String? ?? '',
      category: json['category'] as String? ?? 'General',
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      tareWeightG: (json['tare_weight_g'] as num?)?.toDouble() ?? 0.0,
      description: json['description'] as String?,
      imageUrl: json['image_url'] as String?,
      inventory: json['inventory'] != null
          ? ProductInventory.fromJson(json['inventory'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'sku': sku,
    'barcode': barcode,
    'name': name,
    'category': category,
    'price': price,
    'tare_weight_g': tareWeightG,
    'description': description,
    'image_url': imageUrl,
    'inventory': inventory?.toJson(),
  };

  String get formattedPrice => '\$${price.toStringAsFixed(2)}';
  String get formattedWeight => '${tareWeightG.toStringAsFixed(0)}g';
}
