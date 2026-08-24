/// ResumeRank Pro SDK – public barrel export.
///
/// Usage:
/// ```dart
/// import 'package:resumerank_sdk/resumerank_sdk.dart';
///
/// final client = ResumeRankClient(apiKey: 'your-key');
/// final result = await client.analyze(pdfFile, jobDescription);
/// print(result.finalScore); // e.g. 82.4
/// ```
library resumerank_sdk;

export 'src/client.dart' show ResumeRankClient;
export 'src/models/score_result.dart'
    show ScoreResult, ScoreDetail, AsyncJobAccepted;
export 'src/models/sdk_error.dart' show SdkError, SdkErrorCode;
export 'src/retry_policy.dart' show RetryPolicy;
