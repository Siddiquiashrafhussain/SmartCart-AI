/// SmartCart AI - Cart & Session State Controller

import 'package:flutter/foundation.dart';
import 'package:smartcart_mobile/models/cart_item.dart';
import 'package:smartcart_mobile/models/product.dart';
import 'package:smartcart_mobile/models/session.dart';
import 'package:smartcart_mobile/services/api_service.dart';

class CartController extends ChangeNotifier {
  final ApiService _apiService;

  ShoppingSession? _session;
  final List<CartItem> _localItems = [];
  bool _isLoading = false;
  bool _isScanning = false;
  bool _isBackendConnected = false;
  String? _errorMessage;
  String? _lastSuccessMessage;

  CartController({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  // Getters
  ShoppingSession? get session => _session;
  bool get isLoading => _isLoading;
  bool get isScanning => _isScanning;
  bool get isBackendConnected => _isBackendConnected;
  String? get errorMessage => _errorMessage;
  String? get lastSuccessMessage => _lastSuccessMessage;

  List<CartItem> get items {
    if (_session != null) {
      return _session!.items;
    }
    return _localItems;
  }

  int get totalQuantity {
    if (_session != null) {
      return _session!.totalItems;
    }
    return _localItems.fold(0, (sum, item) => sum + item.quantity);
  }

  double get subtotal {
    if (_session != null) {
      return _session!.subtotal;
    }
    final raw = _localItems.fold<double>(0.0, (sum, item) => sum + item.totalPrice);
    return double.parse(raw.toStringAsFixed(2));
  }

  double get estimatedTax {
    return double.parse((subtotal * 0.0825).toStringAsFixed(2));
  }

  double get grandTotal {
    return double.parse((subtotal + estimatedTax).toStringAsFixed(2));
  }

  String get formattedSubtotal => '\$${subtotal.toStringAsFixed(2)}';
  String get formattedTax => '\$${estimatedTax.toStringAsFixed(2)}';
  String get formattedGrandTotal => '\$${grandTotal.toStringAsFixed(2)}';
  bool get isEmpty => items.isEmpty;

  void clearMessages() {
    _errorMessage = null;
    _lastSuccessMessage = null;
    notifyListeners();
  }

  /// Initialize session with backend
  Future<void> initialize() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _isBackendConnected = await _apiService.checkHealth();
      if (_isBackendConnected) {
        _session = await _apiService.startSession();
        _lastSuccessMessage = 'Connected to SmartCart Server (Session #${_session!.id})';
      } else {
        _errorMessage = 'Backend server offline. Cart operating in local offline preview mode.';
      }
    } catch (e) {
      _isBackendConnected = false;
      _errorMessage = 'Could not establish session: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Scan barcode and add to cart
  Future<bool> scanBarcode(String barcode) async {
    final cleanBarcode = barcode.trim();
    if (cleanBarcode.isEmpty) {
      _errorMessage = 'Barcode cannot be empty.';
      notifyListeners();
      return false;
    }

    _isScanning = true;
    _errorMessage = null;
    _lastSuccessMessage = null;
    notifyListeners();

    try {
      if (_session != null && _isBackendConnected) {
        // Connected mode: sync with backend
        _session = await _apiService.scanBarcode(
          sessionId: _session!.id,
          barcode: cleanBarcode,
        );
        _lastSuccessMessage = 'Item scanned & synced to cart!';
      } else {
        // Offline / fallback mode: lookup product and add locally
        final product = await _apiService.getProductByBarcode(cleanBarcode);
        _addOrIncrementLocalProduct(product);
        _lastSuccessMessage = 'Added "${product.name}" to cart.';
      }
      _isScanning = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _isScanning = false;
      _errorMessage = e.message;
      notifyListeners();
      return false;
    } catch (e) {
      _isScanning = false;
      _errorMessage = 'Failed to scan product: $e';
      notifyListeners();
      return false;
    }
  }

  /// Add a product directly from product catalogue
  Future<bool> addProduct(Product product) async {
    return scanBarcode(product.barcode);
  }

  /// Update item quantity
  Future<void> updateQuantity(int itemId, int newQuantity) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      if (_session != null && _isBackendConnected) {
        _session = await _apiService.updateCartItemQuantity(
          sessionId: _session!.id,
          itemId: itemId,
          quantity: newQuantity,
        );
      } else {
        _updateLocalItemQuantity(itemId, newQuantity);
      }
    } on ApiException catch (e) {
      _errorMessage = e.message;
    } catch (e) {
      _errorMessage = 'Failed to update quantity: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Remove item entirely
  Future<void> removeItem(int itemId) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      if (_session != null && _isBackendConnected) {
        _session = await _apiService.removeCartItem(
          sessionId: _session!.id,
          itemId: itemId,
        );
        _lastSuccessMessage = 'Item removed from cart.';
      } else {
        _localItems.removeWhere((item) => item.id == itemId);
        _lastSuccessMessage = 'Item removed from cart.';
      }
    } on ApiException catch (e) {
      _errorMessage = e.message;
    } catch (e) {
      _errorMessage = 'Failed to remove item: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Clear all items
  void clearCart() {
    _localItems.clear();
    _session = null;
    _lastSuccessMessage = 'Cart cleared.';
    notifyListeners();
  }

  void _addOrIncrementLocalProduct(Product product) {
    final existingIndex = _localItems.indexWhere((i) => i.productId == product.id);
    if (existingIndex >= 0) {
      final existing = _localItems[existingIndex];
      existing.quantity += 1;
      existing.totalPrice = double.parse((existing.quantity * existing.unitPrice).toStringAsFixed(2));
    } else {
      _localItems.add(
        CartItem(
          id: _localItems.length + 1,
          productId: product.id,
          product: product,
          quantity: 1,
          unitPrice: product.price,
          totalPrice: product.price,
        ),
      );
    }
  }

  void _updateLocalItemQuantity(int itemId, int newQuantity) {
    if (newQuantity <= 0) {
      _localItems.removeWhere((i) => i.id == itemId);
    } else {
      final item = _localItems.firstWhere((i) => i.id == itemId);
      item.quantity = newQuantity;
      item.totalPrice = double.parse((item.quantity * item.unitPrice).toStringAsFixed(2));
    }
  }
}
