import 'package:equatable/equatable.dart';
import 'package:meta/meta.dart';
/// Error codes returned by the SDK.
enum SdkErrorCode {
  /// HTTP 401 – missing or invalid API key.
  unauthorized,

  /// HTTP 429 – daily rate limit exceeded.
  rateLimitExceeded,

  /// HTTP 400 – invalid PDF or job description.
  invalidInput,

  /// HTTP 413 – file too large (>10 MB).
  fileTooLarge,

  /// HTTP 422 – Pydantic validation error.
  validationError,

  /// HTTP 5xx – server-side error.
  serverError,

  /// Network error or timeout.
  networkError,

  /// Async job polling exceeded max attempts.
  pollTimeout,

  /// Unknown / unmapped error.
  unknown,
}

/// Structured SDK error – thrown instead of raw exceptions.
@immutable
class SdkError extends Equatable implements Exception {
  const SdkError({
    required this.code,
    required this.message,
    this.statusCode,
    this.retryAfterSeconds,
  });

  final SdkErrorCode code;
  final String message;

  /// HTTP status code if available.
  final int? statusCode;

  /// Populated for [SdkErrorCode.rateLimitExceeded] from Retry-After header.
  final int? retryAfterSeconds;

  /// Maps HTTP status → SdkErrorCode.
  factory SdkError.fromStatusCode(
    int statusCode, {
    String message = '',
    int? retryAfter,
  }) {
    final code = switch (statusCode) {
      401 => SdkErrorCode.unauthorized,
      429 => SdkErrorCode.rateLimitExceeded,
      400 => SdkErrorCode.invalidInput,
      413 => SdkErrorCode.fileTooLarge,
      422 => SdkErrorCode.validationError,
      >= 500 => SdkErrorCode.serverError,
      _ => SdkErrorCode.unknown,
    };
    return SdkError(
      code: code,
      message: message.isEmpty ? 'HTTP $statusCode' : message,
      statusCode: statusCode,
      retryAfterSeconds: retryAfter,
    );
  }

  @override
  String toString() => 'SdkError(code: $code, message: $message)';

  @override
  List<Object?> get props => [code, statusCode, message];
}
