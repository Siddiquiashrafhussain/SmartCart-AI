/// SmartCart AI - Backend REST API Service

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:smartcart_mobile/core/config.dart';
import 'package:smartcart_mobile/models/product.dart';
import 'package:smartcart_mobile/models/session.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;
  final String? detail;

  ApiException({
    required this.statusCode,
    required this.message,
    this.detail,
  });

  @override
  String toString() => message;
}

class ApiService {
  final http.Client _client;

  ApiService({http.Client? client}) : _client = client ?? http.Client();

  String get _baseUrl => AppConfig.apiBaseUrl;

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  /// Verify backend health connectivity
  Future<bool> checkHealth() async {
    try {
      final uri = Uri.parse('$_baseUrl/health');
      final response = await _client.get(uri).timeout(const Duration(seconds: 4));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  /// Fetch catalogue products with optional category and search filters
  Future<List<Product>> getProducts({String? category, String? search}) async {
    try {
      final queryParams = <String, String>{};
      if (category != null && category.isNotEmpty && category != 'All') {
        queryParams['category'] = category;
      }
      if (search != null && search.trim().isNotEmpty) {
        queryParams['search'] = search.trim();
      }

      final uri = Uri.parse('$_baseUrl/products').replace(
        queryParameters: queryParams.isEmpty ? null : queryParams,
      );

      final response = await _client.get(uri, headers: _headers).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((item) => Product.fromJson(item as Map<String, dynamic>)).toList();
      } else {
        _handleError(response);
        return [];
      }
    } on SocketException {
      throw ApiException(
        statusCode: 0,
        message: 'Unable to connect to SmartCart backend at $_baseUrl. Ensure the backend server is running.',
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: 500, message: 'Unexpected network error: $e');
    }
  }

  /// Lookup single product by scanned barcode
  Future<Product> getProductByBarcode(String barcode) async {
    try {
      final cleanBarcode = Uri.encodeComponent(barcode.trim());
      final uri = Uri.parse('$_baseUrl/products/barcode/$cleanBarcode');
      final response = await _client.get(uri, headers: _headers).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return Product.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      } else if (response.statusCode == 404) {
        throw ApiException(
          statusCode: 404,
          message: 'Product with barcode "$barcode" was not found in the store catalog.',
        );
      } else {
        _handleError(response);
        throw ApiException(statusCode: response.statusCode, message: 'Failed to lookup barcode.');
      }
    } on SocketException {
      throw ApiException(
        statusCode: 0,
        message: 'Cannot reach backend server. Check network connection or API URL in settings.',
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: 500, message: 'Error looking up barcode: $e');
    }
  }

  /// Start a new shopping session
  Future<ShoppingSession> startSession({String? userId, String? cartId}) async {
    try {
      final uri = Uri.parse('$_baseUrl/sessions/start');
      final payload = jsonEncode({
        'user_id': userId ?? AppConfig.defaultUserId,
        'cart_id': cartId ?? AppConfig.defaultCartId,
      });

      final response = await _client.post(uri, headers: _headers, body: payload).timeout(const Duration(seconds: 8));

      if (response.statusCode == 201) {
        return ShoppingSession.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      } else {
        _handleError(response);
        throw ApiException(statusCode: response.statusCode, message: 'Failed to start session.');
      }
    } on SocketException {
      throw ApiException(
        statusCode: 0,
        message: 'Cannot start session: Backend server unreachable at $_baseUrl.',
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: 500, message: 'Session start error: $e');
    }
  }

  /// Retrieve current shopping session and cart state
  Future<ShoppingSession> getSession(int sessionId) async {
    try {
      final uri = Uri.parse('$_baseUrl/sessions/$sessionId');
      final response = await _client.get(uri, headers: _headers).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return ShoppingSession.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      } else {
        _handleError(response);
        throw ApiException(statusCode: response.statusCode, message: 'Failed to get session.');
      }
    } on SocketException {
      throw ApiException(statusCode: 0, message: 'Cannot reach server to get session.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: 500, message: 'Get session error: $e');
    }
  }

  /// Scan a barcode and add product to virtual cart in the backend
  Future<ShoppingSession> scanBarcode({
    required int sessionId,
    required String barcode,
    String? idempotencyKey,
  }) async {
    try {
      final uri = Uri.parse('$_baseUrl/sessions/scan');
      final payload = jsonEncode({
        'session_id': sessionId,
        'barcode': barcode.trim(),
        'client_timestamp': DateTime.now().toUtc().toIso8601String(),
        'idempotency_key': idempotencyKey,
      });

      final response = await _client.post(uri, headers: _headers, body: payload).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return ShoppingSession.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      } else if (response.statusCode == 404) {
        throw ApiException(
          statusCode: 404,
          message: 'Scanned barcode "$barcode" does not match any product in store catalogue.',
        );
      } else {
        _handleError(response);
        throw ApiException(statusCode: response.statusCode, message: 'Failed to scan item into cart.');
      }
    } on SocketException {
      throw ApiException(statusCode: 0, message: 'Cannot reach backend server to add item.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: 500, message: 'Scan barcode error: $e');
    }
  }

  /// Update item quantity in virtual cart
  Future<ShoppingSession> updateCartItemQuantity({
    required int sessionId,
    required int itemId,
    required int quantity,
  }) async {
    try {
      final uri = Uri.parse('$_baseUrl/sessions/$sessionId/items/$itemId');
      final payload = jsonEncode({'quantity': quantity});

      final response = await _client.patch(uri, headers: _headers, body: payload).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return ShoppingSession.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      } else {
        _handleError(response);
        throw ApiException(statusCode: response.statusCode, message: 'Failed to update item quantity.');
      }
    } on SocketException {
      throw ApiException(statusCode: 0, message: 'Cannot reach backend server to update quantity.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: 500, message: 'Update quantity error: $e');
    }
  }

  /// Remove item entirely from cart
  Future<ShoppingSession> removeCartItem({
    required int sessionId,
    required int itemId,
  }) async {
    try {
      final uri = Uri.parse('$_baseUrl/sessions/$sessionId/items/$itemId');
      final response = await _client.delete(uri, headers: _headers).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return ShoppingSession.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
      } else {
        _handleError(response);
        throw ApiException(statusCode: response.statusCode, message: 'Failed to remove item.');
      }
    } on SocketException {
      throw ApiException(statusCode: 0, message: 'Cannot reach backend server to remove item.');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(statusCode: 500, message: 'Remove item error: $e');
    }
  }

  void _handleError(http.Response response) {
    try {
      final data = jsonDecode(response.body);
      final detail = data is Map ? (data['detail']?.toString() ?? response.body) : response.body;
      throw ApiException(
        statusCode: response.statusCode,
        message: detail,
        detail: detail,
      );
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(
        statusCode: response.statusCode,
        message: 'HTTP ${response.statusCode}: ${response.reasonPhrase}',
      );
    }
  }
}
