/// SmartCart AI - Product Catalogue & Search Screen

import 'package:flutter/material.dart';
import 'package:smartcart_mobile/core/theme.dart';
import 'package:smartcart_mobile/models/product.dart';
import 'package:smartcart_mobile/services/api_service.dart';
import 'package:smartcart_mobile/services/cart_controller.dart';
import 'package:smartcart_mobile/widgets/product_card.dart';

class CatalogScreen extends StatefulWidget {
  final CartController cartController;
  final ApiService apiService;

  const CatalogScreen({
    super.key,
    required this.cartController,
    required this.apiService,
  });

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  final TextEditingController _searchController = TextEditingController();
  List<Product> _products = [];
  bool _isLoading = true;
  String? _errorMessage;
  String _selectedCategory = 'All';

  static const List<String> _categories = [
    'All',
    'Breakfast & Cereal',
    'Dairy & Refrigerated',
    'Bakery',
    'Beverages',
    'Snacks',
    'Pantry & Staples',
  ];

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadProducts() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final items = await widget.apiService.getProducts(
        category: _selectedCategory == 'All' ? null : _selectedCategory,
        search: _searchController.text.trim().isEmpty ? null : _searchController.text.trim(),
      );
      setState(() {
        _products = items;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _onAddToCart(Product product) async {
    final success = await widget.cartController.addProduct(product);
    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Row(
            children: [
              const Icon(Icons.check_circle, color: Colors.white, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text('Added "${product.name}" to cart'),
              ),
            ],
          ),
          backgroundColor: AppTheme.successGreen,
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } else {
      final err = widget.cartController.errorMessage ?? 'Could not add to cart';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(err),
          backgroundColor: AppTheme.errorRed,
          duration: const Duration(seconds: 3),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Store Catalogue'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Products',
            onPressed: _loadProducts,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search Bar
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search products by name...',
                prefixIcon: const Icon(Icons.search, color: AppTheme.textMuted),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          _loadProducts();
                        },
                      )
                    : null,
                isDense: true,
              ),
              onSubmitted: (_) => _loadProducts(),
            ),
          ),

          // Category Chips Horizontal Scroll
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              itemCount: _categories.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, index) {
                final cat = _categories[index];
                final isSelected = cat == _selectedCategory;
                return ChoiceChip(
                  label: Text(
                    cat,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                      color: isSelected ? Colors.white : AppTheme.textDark,
                    ),
                  ),
                  selected: isSelected,
                  selectedColor: AppTheme.primaryBlue,
                  backgroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                    side: BorderSide(
                      color: isSelected ? AppTheme.primaryBlue : const Color(0xFFE2E8F0),
                    ),
                  ),
                  showCheckmark: false,
                  onSelected: (selected) {
                    if (selected) {
                      setState(() => _selectedCategory = cat);
                      _loadProducts();
                    }
                  },
                );
              },
            ),
          ),
          const SizedBox(height: 8),

          // Main Product List or States
          Expanded(
            child: RefreshIndicator(
              onRefresh: _loadProducts,
              child: _buildBody(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 12),
            Text('Loading store catalog...', style: TextStyle(color: AppTheme.textMuted)),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_off_outlined, size: 56, color: AppTheme.errorRed),
              const SizedBox(height: 12),
              const Text(
                'Could not load catalogue',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textDark),
              ),
              const SizedBox(height: 6),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _loadProducts,
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_products.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.search_off_outlined, size: 54, color: AppTheme.textMuted),
            const SizedBox(height: 12),
            const Text(
              'No products found',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textDark),
            ),
            const SizedBox(height: 4),
            Text(
              _searchController.text.isNotEmpty
                  ? 'No items match "${_searchController.text}" in $_selectedCategory.'
                  : 'No items found in category $_selectedCategory.',
              style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.only(bottom: 20),
      itemCount: _products.length,
      itemBuilder: (context, index) {
        final product = _products[index];
        return ProductCard(
          product: product,
          onAddToCart: () => _onAddToCart(product),
        );
      },
    );
  }
}
