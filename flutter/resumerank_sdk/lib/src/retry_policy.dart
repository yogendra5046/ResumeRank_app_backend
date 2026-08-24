import 'package:meta/meta.dart';
import 'client.dart';

/// Controls retry behaviour for the [ResumeRankClient].
@immutable
class RetryPolicy {
  const RetryPolicy({
    this.maxAttempts = 3,
    this.initialDelay = const Duration(milliseconds: 500),
    this.maxDelay = const Duration(seconds: 8),
    this.backoffMultiplier = 2.0,
    this.pollMaxAttempts = 30,
    this.pollInterval = const Duration(seconds: 3),
  });

  /// Maximum number of retry attempts for transient errors (5xx, network).
  final int maxAttempts;

  /// Initial delay before first retry.
  final Duration initialDelay;

  /// Maximum delay between retries (exponential backoff cap).
  final Duration maxDelay;

  /// Exponential backoff multiplier.
  final double backoffMultiplier;

  /// Maximum number of times to poll /status/{job_id} for a 202 response.
  final int pollMaxAttempts;

  /// Delay between poll attempts.
  final Duration pollInterval;

  /// Default policy suitable for most use cases.
  static const RetryPolicy defaultPolicy = RetryPolicy();

  /// Aggressive policy for time-sensitive scenarios.
  static const RetryPolicy aggressive = RetryPolicy(
    maxAttempts: 5,
    initialDelay: Duration(milliseconds: 200),
    pollInterval: Duration(seconds: 2),
    pollMaxAttempts: 60,
  );

  Duration delayForAttempt(int attempt) {
    final ms = initialDelay.inMilliseconds *
        (backoffMultiplier * attempt).ceil().clamp(1, 1 << 20);
    return Duration(
      milliseconds: ms.clamp(initialDelay.inMilliseconds, maxDelay.inMilliseconds),
    );
  }
}
