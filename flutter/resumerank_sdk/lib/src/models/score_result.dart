import 'package:equatable/equatable.dart';
import 'package:meta/meta.dart';

/// Outcome of a successful ATS analysis.
@immutable
class ScoreResult extends Equatable {
  const ScoreResult({
    required this.overallScore,
    required this.grade,
    required this.impact,
    required this.format,
    required this.skillGap,
    required this.atsParse,
    this.fromCache = false,
    this.rawResumeText = '',
    this.rawJdText = '',
  });

  final int overallScore;
  final String grade;
  final ScoreDetail impact;
  final ScoreDetail format;
  final SkillGapDetail skillGap;
  final ScoreDetail atsParse;
  final bool fromCache;
  final String rawResumeText;
  final String rawJdText;

  factory ScoreResult.fromJson(Map<String, dynamic> json) => ScoreResult(
        overallScore: (json['overall_score'] as num?)?.toInt() ?? 0,
        grade: json['grade'] as String? ?? 'D',
        impact: ScoreDetail.fromJson(json['impact'] ?? {}),
        format: ScoreDetail.fromJson(json['format'] ?? {}),
        skillGap: SkillGapDetail.fromJson(json['skill_gap'] ?? {}),
        atsParse: ScoreDetail.fromJson(json['ats_parse'] ?? {}),
        fromCache: json['from_cache'] as bool? ?? false,
        rawResumeText: json['raw_resume_text'] as String? ?? '',
        rawJdText: json['raw_jd_text'] as String? ?? '',
      );

  @override
  List<Object?> get props => [overallScore, fromCache];
}

@immutable
class ScoreDetail extends Equatable {
  const ScoreDetail({
    required this.score,
    required this.details,
    this.debugText,
  });

  final int score;
  final List<String> details;
  final String? debugText;

  factory ScoreDetail.fromJson(Map<String, dynamic> json) => ScoreDetail(
        score: (json['score'] as num?)?.toInt() ?? 0,
        details: List<String>.from(json['details'] ?? []),
        debugText: json['debug_text'] as String?,
      );

  @override
  List<Object?> get props => [score, details];
}

@immutable
class SkillGapDetail extends Equatable {
  const SkillGapDetail({
    required this.matchPercent,
    required this.matchedSkills,
    required this.missingSkills,
    required this.skillGraphData,
  });

  final int matchPercent;
  final List<String> matchedSkills;
  final List<String> missingSkills;
  final List<SkillGraphItem> skillGraphData;

  factory SkillGapDetail.fromJson(Map<String, dynamic> json) => SkillGapDetail(
        matchPercent: (json['match_percent'] as num?)?.toInt() ?? 0,
        matchedSkills: List<String>.from(json['matched_skills'] ?? []),
        missingSkills: List<String>.from(json['missing_skills'] ?? []),
        skillGraphData: (json['skill_graph_data'] as List?)
                ?.map((e) => SkillGraphItem.fromJson(e))
                .toList() ??
            [],
      );

  @override
  List<Object?> get props => [matchPercent, matchedSkills, missingSkills];
}

@immutable
class SkillGraphItem extends Equatable {
  const SkillGraphItem({
    required this.skill,
    required this.status,
    required this.jdCount,
    required this.resumeCount,
  });

  final String skill;
  final String status;
  final int jdCount;
  final int resumeCount;

  factory SkillGraphItem.fromJson(Map<String, dynamic> json) => SkillGraphItem(
        skill: json['skill'] as String? ?? '',
        status: json['status'] as String? ?? '',
        jdCount: (json['jd_count'] as num?)?.toInt() ?? 0,
        resumeCount: (json['resume_count'] as num?)?.toInt() ?? 0,
      );

  @override
  List<Object?> get props => [skill, status];
}

/// Returned when the server responds with 202 (async processing).
@immutable
class AsyncJobAccepted extends Equatable {
  const AsyncJobAccepted({
    required this.jobId,
    required this.pollUrl,
  });

  final String jobId;
  final String pollUrl;

  factory AsyncJobAccepted.fromJson(Map<String, dynamic> json) =>
      AsyncJobAccepted(
        jobId: json['job_id'] as String,
        pollUrl: json['poll_url'] as String,
      );

  @override
  List<Object?> get props => [jobId];
}
