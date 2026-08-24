import 'dart:convert';
//import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:resumerank_sdk/resumerank_sdk.dart';

// ── Helpers ───────────────────────────────────────────────────────────────────

Map<String, dynamic> _scoreJson({int overall = 82}) => {
      'overall_score': overall,
      'grade': 'B',
      'impact': {
        'score': 80,
        'details': ['impact details']
      },
      'format': {
        'score': 100,
        'details': ['format details']
      },
      'skill_gap': {
        'match_percent': 75,
        'matched_skills': ['python'],
        'missing_skills': [],
        'skill_graph_data': [
            {'skill': 'python', 'status': 'matched', 'jd_count': 1, 'resume_count': 1}
        ]
      },
      'ats_parse': {
        'score': 90,
        'details': ['ats parsed']
      },
      'from_cache': false,
      'raw_resume_text': 'resume text',
      'raw_jd_text': 'jd text'
    };

ResumeRankClient _clientWith(MockClient mock) => ResumeRankClient(
      apiKey: 'test-key',
      baseUrl: 'http://localhost',
      httpClient: mock,
    );

// ── Tests ─────────────────────────────────────────────────────────────────────

void main() {
  group('ResumeRankClient.analyze', () {
    test('returns ScoreResult on HTTP 200', () async {
      final mock = MockClient((_) async => http.Response(
            jsonEncode(_scoreJson()),
            200,
            headers: {'content-type': 'application/json'},
          ));

      final client = _clientWith(mock);
      final result = await client.analyzeBytes(
        [1, 2, 3, 4],
        'resume.pdf',
        'Senior Python Engineer needed with 5+ years experience.',
      );

      expect(result.overallScore, 82);
      expect(result.grade, 'B');
      expect(result.skillGap.matchedSkills, hasLength(1));
      expect(result.skillGap.matchedSkills.first, 'python');
      client.dispose();
    });

    test('polls /status on HTTP 202 until done', () async {
      var callCount = 0;
      final mock = MockClient((request) async {
        callCount++;
        if (callCount == 1) {
          // First call: POST /v1/analyze → 202
          return http.Response(
            jsonEncode({
              'status': 'accepted',
              'job_id': 'test-job-id',
              'poll_url': 'http://localhost/status/test-job-id',
            }),
            202,
            headers: {'content-type': 'application/json'},
          );
        }
        if (callCount == 2) {
          // First poll → still pending
          return http.Response(
            jsonEncode({'job_id': 'test-job-id', 'status': 'processing'}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        // Second poll → done
        return http.Response(
          jsonEncode({
            'job_id': 'test-job-id',
            'status': 'done',
            'result': _scoreJson(overall: 77),
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = ResumeRankClient(
        apiKey: 'test-key',
        baseUrl: 'http://localhost',
        httpClient: mock,
        retryPolicy: const RetryPolicy(
          pollInterval: Duration(milliseconds: 1),
          pollMaxAttempts: 10,
        ),
      );

      final result = await client.analyzeBytes(
        [1, 2, 3],
        'resume.pdf',
        'Engineer needed.',
      );

      expect(result.overallScore, 77);
      expect(callCount, greaterThanOrEqualTo(3));
      client.dispose();
    });

    test('throws SdkError with code unauthorized on HTTP 401', () async {
      final mock = MockClient((_) async => http.Response(
            jsonEncode({'detail': 'X-API-Key header is required'}),
            401,
          ));
      final client = _clientWith(mock);

      expect(
        () => client.analyzeBytes([1], 'r.pdf', 'jd'),
        throwsA(isA<SdkError>().having(
          (e) => e.code,
          'code',
          SdkErrorCode.unauthorized,
        )),
      );
      client.dispose();
    });

    test('throws SdkError with code rateLimitExceeded on HTTP 429', () async {
      final mock = MockClient((_) async => http.Response(
            jsonEncode({'detail': 'Rate limit exceeded'}),
            429,
            headers: {'retry-after': '86400'},
          ));
      final client = _clientWith(mock);

      expect(
        () => client.analyzeBytes([1], 'r.pdf', 'jd'),
        throwsA(isA<SdkError>()
            .having((e) => e.code, 'code', SdkErrorCode.rateLimitExceeded)
            .having((e) => e.retryAfterSeconds, 'retryAfter', 86400)),
      );
      client.dispose();
    });

    test('retries on 503 and succeeds on second attempt', () async {
      var calls = 0;
      final mock = MockClient((_) async {
        calls++;
        if (calls == 1) {
          return http.Response('Service Unavailable', 503);
        }
        return http.Response(
          jsonEncode(_scoreJson()),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = ResumeRankClient(
        apiKey: 'key',
        baseUrl: 'http://localhost',
        httpClient: mock,
        retryPolicy: const RetryPolicy(
          maxAttempts: 2,
          initialDelay: Duration(milliseconds: 1),
        ),
      );
      final result = await client.analyzeBytes([1], 'r.pdf', 'jd');
      expect(result.overallScore, greaterThan(0));
      expect(calls, 2);
      client.dispose();
    });

    test('poll timeout throws SdkError with pollTimeout code', () async {
      final mock = MockClient((request) async {
        if (request.method == 'POST') {
          return http.Response(
            jsonEncode({
              'status': 'accepted',
              'job_id': 'job-x',
              'poll_url': 'http://localhost/status/job-x',
            }),
            202,
            headers: {'content-type': 'application/json'},
          );
        }
        // Always pending
        return http.Response(
          jsonEncode({'job_id': 'job-x', 'status': 'pending'}),
          200,
          headers: {'content-type': 'application/json'},
        );
      });

      final client = ResumeRankClient(
        apiKey: 'key',
        baseUrl: 'http://localhost',
        httpClient: mock,
        retryPolicy: const RetryPolicy(
          pollMaxAttempts: 2,
          pollInterval: Duration(milliseconds: 1),
        ),
      );

      expect(
        () => client.analyzeBytes([1], 'r.pdf', 'jd'),
        throwsA(isA<SdkError>()
            .having((e) => e.code, 'code', SdkErrorCode.pollTimeout)),
      );
      client.dispose();
    });
  });

  group('ScoreResult.fromJson', () {
    test('parses all fields correctly', () {
      final result = ScoreResult.fromJson(_scoreJson());
      expect(result.overallScore, 82);
      expect(result.grade, 'B');
      expect(result.fromCache, isFalse);
      expect(result.skillGap.matchedSkills.first, 'python');
      expect(result.impact.details.isNotEmpty, isTrue);
    });
  });

  group('SdkError', () {
    test('fromStatusCode maps 401 to unauthorized', () {
      final err = SdkError.fromStatusCode(401, message: 'no key');
      expect(err.code, SdkErrorCode.unauthorized);
    });

    test('fromStatusCode maps 500 to serverError', () {
      final err = SdkError.fromStatusCode(500);
      expect(err.code, SdkErrorCode.serverError);
    });
  });

  group('RetryPolicy', () {
    test('delayForAttempt is clamped to maxDelay', () {
      const policy = RetryPolicy(
        initialDelay: Duration(seconds: 1),
        maxDelay: Duration(seconds: 4),
        backoffMultiplier: 3.0,
        maxAttempts: 5,
        pollMaxAttempts: 10,
        pollInterval: Duration(seconds: 1),
      );
      final delay = policy.delayForAttempt(10);
      expect(delay.inSeconds, lessThanOrEqualTo(4));
    });
  });
}
