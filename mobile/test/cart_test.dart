/// SmartCart AI - Cart Calculations & State Transition Unit Tests

import 'package:flutter_test/flutter_test.dart';
import 'package:smartcart_mobile/models/cart_item.dart';
import 'package:smartcart_mobile/models/product.dart';
import 'package:smartcart_mobile/models/session.dart';
import 'package:smartcart_mobile/services/cart_controller.dart';

void main() {
  group('Cart Calculations & Math', () {
    final testProductA = Product(
      id: 1,
      sku: 'SKU-001',
      barcode: '8901030018241',
      name: 'Organic Whole Wheat Cereal',
      category: 'Breakfast & Cereal',
      price: 4.99,
      tareWeightG: 500.0,
    );

    final testProductB = Product(
      id: 2,
      sku: 'SKU-002',
      barcode: '8901030029312',
      name: 'Whole Milk Gallon',
      category: 'Dairy & Refrigerated',
      price: 3.79,
      tareWeightG: 3780.0,
    );

    test('CartItem calculates unit price and line subtotal without rounding drift', () {
      final item = CartItem(
        id: 101,
        productId: testProductA.id,
        product: testProductA,
        quantity: 3,
        unitPrice: 4.99,
        totalPrice: 14.97,
      );

      expect(item.quantity, 3);
      expect(item.unitPrice, 4.99);
      expect(item.totalPrice, 14.97);
      expect(item.formattedUnitPrice, '\$4.99');
      expect(item.formattedTotalPrice, '\$14.97');

      final updated = item.copyWith(quantity: 4);
      expect(updated.quantity, 4);
      expect(updated.totalPrice, 19.96);
      expect(updated.formattedTotalPrice, '\$19.96');
    });

    test('ShoppingSession accurately computes subtotal, estimated tax, and grand total', () {
      final session = ShoppingSession(
        id: 42,
        userId: 'shopper_test',
        cartId: 'CART-001',
        status: 'ACTIVE',
        startedAt: DateTime.now(),
        items: [
          CartItem(
            id: 1,
            productId: testProductA.id,
            product: testProductA,
            quantity: 2,
            unitPrice: 4.99,
            totalPrice: 9.98,
          ),
          CartItem(
            id: 2,
            productId: testProductB.id,
            product: testProductB,
            quantity: 1,
            unitPrice: 3.79,
            totalPrice: 3.79,
          ),
        ],
        totalItems: 3,
        subtotal: 13.77,
      );

      expect(session.subtotal, 13.77);
      expect(session.formattedSubtotal, '\$13.77');

      // Tax at 8.25%: 13.77 * 0.0825 = 1.136025 -> 1.14
      expect(session.estimatedTax, 1.14);
      expect(session.formattedTax, '\$1.14');

      // Grand total: 13.77 + 1.14 = 14.91
      expect(session.grandTotal, 14.91);
      expect(session.formattedGrandTotal, '\$14.91');
    });
  });

  group('CartController State Transitions (Offline / Preview Mode)', () {
    late CartController controller;

    final testProduct = Product(
      id: 1,
      sku: 'SKU-001',
      barcode: '8901030018241',
      name: 'Organic Whole Wheat Cereal',
      category: 'Breakfast & Cereal',
      price: 4.99,
      tareWeightG: 500.0,
    );

    setUp(() {
      controller = CartController();
    });

    test('Initial cart state is empty and has 0 totals', () {
      expect(controller.isEmpty, isTrue);
      expect(controller.items.length, 0);
      expect(controller.totalQuantity, 0);
      expect(controller.subtotal, 0.0);
      expect(controller.formattedSubtotal, '\$0.00');
      expect(controller.formattedGrandTotal, '\$0.00');
    });

    test('Adding product increments item quantity and recalculates totals', () async {
      // Simulate local adding
      controller.testAddProduct(testProduct);

      expect(controller.isEmpty, isFalse);
      expect(controller.items.length, 1);
      expect(controller.items.first.quantity, 1);
      expect(controller.totalQuantity, 1);
      expect(controller.subtotal, 4.99);

      // Add same product again -> quantity increments
      controller.testAddProduct(testProduct);

      expect(controller.items.length, 1);
      expect(controller.items.first.quantity, 2);
      expect(controller.totalQuantity, 2);
      expect(controller.subtotal, 9.98);
    });

    test('Updating quantity adjusts item total and cart subtotal', () {
      controller.testAddProduct(testProduct);
      final itemId = controller.items.first.id;

      // Update quantity to 5
      controller.updateQuantity(itemId, 5);

      expect(controller.items.first.quantity, 5);
      expect(controller.totalQuantity, 5);
      expect(controller.subtotal, 24.95);

      // Decrementing to 0 removes the item
      controller.updateQuantity(itemId, 0);
      expect(controller.isEmpty, isTrue);
      expect(controller.totalQuantity, 0);
      expect(controller.subtotal, 0.0);
    });

    test('Removing item deletes it from cart', () {
      controller.testAddProduct(testProduct);
      final itemId = controller.items.first.id;

      controller.removeItem(itemId);
      expect(controller.isEmpty, isTrue);
      expect(controller.totalQuantity, 0);
    });

    test('Empty barcode produces validation error', () async {
      final success = await controller.scanBarcode('');
      expect(success, isFalse);
      expect(controller.errorMessage, contains('cannot be empty'));
    });
  });
}

extension CartControllerTestHelper on CartController {
  void testAddProduct(Product product) {
    final existingIndex = items.indexWhere((i) => i.productId == product.id);
    if (existingIndex >= 0) {
      final existing = items[existingIndex];
      existing.quantity += 1;
      existing.totalPrice = double.parse((existing.quantity * existing.unitPrice).toStringAsFixed(2));
    } else {
      items.add(
        CartItem(
          id: items.length + 1,
          productId: product.id,
          product: product,
          quantity: 1,
          unitPrice: product.price,
          totalPrice: product.price,
        ),
      );
    }
    notifyListeners();
  }
}
