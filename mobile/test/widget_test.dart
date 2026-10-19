/// SmartCart AI - App Navigation & Widget Smoke Tests

import 'package:flutter_test/flutter_test.dart';
import 'package:smartcart_mobile/main.dart';

void main() {
  testWidgets('SmartCartApp smoke test renders navigation and tabs', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartCartApp());
    await tester.pump();

    // Verify main app title and Scan & Go labels
    expect(find.text('SmartCart AI'), findsOneWidget);
    expect(find.text('Scan & Go'), findsWidgets);

    // Verify bottom navigation bar destinations
    expect(find.text('Catalogue'), findsOneWidget);
    expect(find.text('Cart'), findsOneWidget);
  });
}
