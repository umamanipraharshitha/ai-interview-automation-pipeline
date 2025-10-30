import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;

class HomeScreen extends StatefulWidget {
  final String email; // ✅ Email passed from login

  const HomeScreen({Key? key, required this.email}) : super(key: key);

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _uploading = false;

  /// 🔹 Upload file to FastAPI backend
  Future<void> _uploadFile() async {
    final result = await FilePicker.platform.pickFiles(withData: true);
    if (result == null) return;

    final file = result.files.first;
    final bytes = file.bytes!;
    final fileName = file.name;

    setState(() => _uploading = true);

    try {
      final uri = Uri.parse("http://127.0.0.1:5000/upload/resume");

      final request = http.MultipartRequest("POST", uri)
        ..fields['user_id'] = widget.email // ✅ send email as ID
        ..files.add(http.MultipartFile.fromBytes("file", bytes, filename: fileName));

      final response = await request.send();
      final res = await http.Response.fromStream(response);

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("✅ Resume uploaded successfully!")),
        );
      } else {
        final data = jsonDecode(res.body);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("⚠️ Upload failed: ${data['detail'] ?? res.body}")),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("❌ Error: $e")),
      );
    }

    setState(() => _uploading = false);
  }

  void _logout() {
    Navigator.pushReplacementNamed(context, '/');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Welcome, ${widget.email}"),
        actions: [
          IconButton(onPressed: _logout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton.icon(
                onPressed: _uploading ? null : _uploadFile,
                icon: const Icon(Icons.cloud_upload),
                label: const Text("Upload Resume"),
              ),
              const SizedBox(height: 20),
              if (_uploading) const CircularProgressIndicator(),
            ],
          ),
        ),
      ),
    );
  }
}
