import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'models/score_result.dart';
import 'models/sdk_error.dart';
import 'retry_policy.dart';

/// Official client for the ResumeRank Pro ATS API.
///
/// ```dart
/// final client = ResumeRankClient(apiKey: 'your-key');
/// final result = await client.analyze(File('resume.pdf'), jobDescription);
/// print('Score: ${result.finalScore} (${result.grade})');
/// ```
class ResumeRankClient {
  ResumeRankClient({
    required this.apiKey,
    String baseUrl = 'https://api.resumerank.pro',
    RetryPolicy retryPolicy = RetryPolicy.defaultPolicy,
    http.Client? httpClient,
    Duration requestTimeout = const Duration(seconds: 30),
  })  : _baseUrl = baseUrl.endsWith('/')
            ? baseUrl.substring(0, baseUrl.length - 1)
            : baseUrl,
        _retry = retryPolicy,
        _client = httpClient ?? http.Client(),
        _timeout = requestTimeout;

  /// API key sent in `X-API-Key` header.
  final String apiKey;

  final String _baseUrl;
  final RetryPolicy _retry;
  final http.Client _client;
  final Duration _timeout;

  /// Analyze a PDF resume against a job description.
  ///
  /// Handles:
  /// - Automatic retry on transient 5xx / network errors.
  /// - 202 Accepted → polling /status/{job_id} until done.
  /// - Maps all HTTP errors to typed [SdkError].
  ///
  /// Throws [SdkError] on unrecoverable errors.
  Future<ScoreResult> analyze(File pdf, String jobDescription) async {
    final bytes = await pdf.readAsBytes();
    return _analyzeBytes(bytes, pdf.path.split('/').last, jobDescription);
  }

  /// Analyze raw PDF bytes (useful when file access is abstracted).
  Future<ScoreResult> analyzeBytes(
    List<int> pdfBytes,
    String filename,
    String jobDescription,
  ) =>
      _analyzeBytes(pdfBytes, filename, jobDescription);

  Future<ScoreResult> _analyzeBytes(
    List<int> pdfBytes,
    String filename,
    String jobDescription,
  ) async {
    final uri = Uri.parse('$_baseUrl/v1/analyze');

    for (var attempt = 0; attempt <= _retry.maxAttempts; attempt++) {
      try {
        final request = http.MultipartRequest('POST', uri)
          ..headers['X-API-Key'] = apiKey
          ..fields['job_description'] = jobDescription
          ..files.add(
            http.MultipartFile.fromBytes(
              'resume',
              pdfBytes,
              filename: filename,
            ),
          );

        final streamed = await _client
            .send(request)
            .timeout(_timeout, onTimeout: _onTimeout);
        final response = await http.Response.fromStream(streamed);

        if (response.statusCode == 200) {
          final json = jsonDecode(response.body) as Map<String, dynamic>;
          return ScoreResult.fromJson(json);
        }

        if (response.statusCode == 202) {
          final json = jsonDecode(response.body) as Map<String, dynamic>;
          final accepted = AsyncJobAccepted.fromJson(json);
          return _pollUntilDone(accepted.jobId);
        }

        // Non-retryable client errors
        if (response.statusCode == 401 ||
            response.statusCode == 413 ||
            response.statusCode == 422 ||
            response.statusCode == 400) {
          throw SdkError.fromStatusCode(
            response.statusCode,
            message: _extractDetail(response.body),
          );
        }

        if (response.statusCode == 429) {
          final retryAfter = int.tryParse(
            response.headers['retry-after'] ?? '',
          );
          throw SdkError.fromStatusCode(
            429,
            message: _extractDetail(response.body),
            retryAfter: retryAfter,
          );
        }

        // 5xx – retryable
        if (attempt < _retry.maxAttempts) {
          await Future<void>.delayed(_retry.delayForAttempt(attempt));
          continue;
        }
        throw SdkError.fromStatusCode(
          response.statusCode,
          message: _extractDetail(response.body),
        );
      } on SdkError {
        rethrow;
      } on TimeoutException catch (e) {
        if (attempt < _retry.maxAttempts) {
          await Future<void>.delayed(_retry.delayForAttempt(attempt));
          continue;
        }
        throw SdkError(
          code: SdkErrorCode.networkError,
          message: 'Request timed out: $e',
        );
      } on SocketException catch (e) {
        if (attempt < _retry.maxAttempts) {
          await Future<void>.delayed(_retry.delayForAttempt(attempt));
          continue;
        }
        throw SdkError(
          code: SdkErrorCode.networkError,
          message: 'Network error: ${e.message}',
        );
      }
    }

    // Should not reach here
    throw const SdkError(
      code: SdkErrorCode.unknown,
      message: 'Unexpected SDK state',
    );
  }

  /// Poll /status/{jobId} until the job is done or we exceed max attempts.
  Future<ScoreResult> _pollUntilDone(String jobId) async {
    final uri = Uri.parse('$_baseUrl/status/$jobId');

    for (var attempt = 0; attempt < _retry.pollMaxAttempts; attempt++) {
      await Future<void>.delayed(_retry.pollInterval);

      try {
        final response = await _client.get(
          uri,
          headers: {'X-API-Key': apiKey},
        ).timeout(_timeout, onTimeout: _onTimeout);

        if (response.statusCode != 200) {
          throw SdkError.fromStatusCode(
            response.statusCode,
            message: _extractDetail(response.body),
          );
        }

        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final status = json['status'] as String;

        switch (status) {
          case 'done':
            return ScoreResult.fromJson(
              json['result'] as Map<String, dynamic>,
            );
          case 'failed':
            throw SdkError(
              code: SdkErrorCode.serverError,
              message: json['error'] as String? ?? 'Job failed',
            );
          case 'pending':
          case 'processing':
            // Continue polling
            break;
        }
      } on SdkError {
        rethrow;
      } on Exception catch (e) {
        // Non-fatal poll error – retry
        if (attempt == _retry.pollMaxAttempts - 1) {
          throw SdkError(
            code: SdkErrorCode.networkError,
            message: 'Poll error: $e',
          );
        }
      }
    }

    throw SdkError(
      code: SdkErrorCode.pollTimeout,
      message:
          'Job did not complete after ${_retry.pollMaxAttempts} poll attempts '
          '(${_retry.pollMaxAttempts * _retry.pollInterval.inSeconds}s)',
    );
  }

  static Never _onTimeout() {
    throw const SdkError(
      code: SdkErrorCode.networkError,
      message: 'HTTP request timed out',
    );
  }

  static String _extractDetail(String body) {
    try {
      final json = jsonDecode(body) as Map<String, dynamic>;
      return json['detail']?.toString() ?? body;
    } catch (_) {
      return body;
    }
  }

  /// Release the underlying HTTP client. Call when done with the SDK.
  void dispose() => _client.close();
}
