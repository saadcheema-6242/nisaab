import type * as HttpClient from '@effect/platform/HttpClient'
import * as HttpClientError from '@effect/platform/HttpClientError'
import * as HttpClientRequest from '@effect/platform/HttpClientRequest'
import * as HttpClientResponse from '@effect/platform/HttpClientResponse'
import * as Data from 'effect/Data'
import * as Effect from 'effect/Effect'
import type { ParseError } from 'effect/ParseResult'
import * as S from 'effect/Schema'

export class HealthCheckHealthGet200 extends S.Struct({}) {}

/**
 * FSc group
 */
export class StudentProfileDtoGroupCode extends S.Literal(
  'PRE_MED',
  'PRE_ENG',
  'ICS',
) {}

/**
 * Language the tutor explains in: English, Urdu or Roman Urdu
 */
export class StudentProfileDtoExplanationLanguage extends S.Literal(
  'en',
  'ur',
  'ur-Latn',
) {}

/**
 * The student's FSc details.
 */
export class StudentProfileDto extends S.Class<StudentProfileDto>(
  'StudentProfileDto',
)({
  /**
   * ID of the user
   */
  user_id: S.String,
  /**
   * Grade: 11 (HSSC-I) or 12 (HSSC-II)
   */
  grade: S.Int,
  /**
   * FSc group
   */
  group_code: StudentProfileDtoGroupCode,
  /**
   * Language the tutor explains in: English, Urdu or Roman Urdu
   */
  explanation_language: StudentProfileDtoExplanationLanguage,
  /**
   * Year of the student's annual exam
   */
  exam_year: S.optionalWith(S.Int, { nullable: true }),
  /**
   * When onboarding was completed
   */
  onboarding_completed_at: S.optionalWith(S.String, { nullable: true }),
}) {}

/**
 * Whether the student has completed onboarding, and their profile if so.
 */
export class ProfileStateDto extends S.Class<ProfileStateDto>(
  'ProfileStateDto',
)({
  /**
   * True once onboarding is complete
   */
  onboarded: S.Boolean,
  /**
   * The student's profile
   */
  profile: S.optionalWith(StudentProfileDto, { nullable: true }),
}) {}

export class ProfileUpdateExplanationLanguageEnum extends S.Literal(
  'en',
  'ur',
  'ur-Latn',
) {}

export class ProfileUpdate extends S.Class<ProfileUpdate>('ProfileUpdate')({
  /**
   * Tutor language: English, Urdu or Roman Urdu
   */
  explanation_language: S.optionalWith(ProfileUpdateExplanationLanguageEnum, {
    nullable: true,
  }),
  /**
   * Year of the annual exam
   */
  exam_year: S.optionalWith(
    S.Int.pipe(S.greaterThanOrEqualTo(2025), S.lessThanOrEqualTo(2035)),
    { nullable: true },
  ),
}) {}

export class ValidationError extends S.Class<ValidationError>(
  'ValidationError',
)({
  loc: S.Array(S.Union(S.String, S.Int)),
  msg: S.String,
  type: S.String,
}) {}

export class HTTPValidationError extends S.Class<HTTPValidationError>(
  'HTTPValidationError',
)({
  detail: S.optionalWith(S.Array(ValidationError), { nullable: true }),
}) {}

/**
 * Grade: 11 (HSSC-I) or 12 (HSSC-II)
 */
export class OnboardingRequestGrade extends S.Literal(11, 12) {}

/**
 * FSc group
 */
export class OnboardingRequestGroupCode extends S.Literal(
  'PRE_MED',
  'PRE_ENG',
  'ICS',
) {}

/**
 * Tutor language: English, Urdu or Roman Urdu
 */
export class OnboardingRequestExplanationLanguage extends S.Literal(
  'en',
  'ur',
  'ur-Latn',
) {}

export class OnboardingRequest extends S.Class<OnboardingRequest>(
  'OnboardingRequest',
)({
  /**
   * Grade: 11 (HSSC-I) or 12 (HSSC-II)
   */
  grade: OnboardingRequestGrade,
  /**
   * FSc group
   */
  group_code: OnboardingRequestGroupCode,
  /**
   * Tutor language: English, Urdu or Roman Urdu
   */
  explanation_language: S.optionalWith(OnboardingRequestExplanationLanguage, {
    nullable: true,
    default: () => 'en' as const,
  }),
  /**
   * Year of the annual exam
   */
  exam_year: S.optionalWith(
    S.Int.pipe(S.greaterThanOrEqualTo(2025), S.lessThanOrEqualTo(2035)),
    { nullable: true },
  ),
}) {}

export class ProjectDto extends S.Class<ProjectDto>('ProjectDto')({
  /**
   * Unique ID of the project
   */
  id: S.String,
  /**
   * ID of the user who owns the project
   */
  owner_id: S.String,
  /**
   * Name of the project
   */
  name: S.String,
  /**
   * Description of the project
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * Language code for the project: en, ur or ur-Latn (Roman Urdu)
   */
  language_code: S.String,
  /**
   * subject_workspace (one FBISE subject, created by onboarding) or custom
   */
  kind: S.optionalWith(S.String, {
    nullable: true,
    default: () => 'custom' as const,
  }),
  /**
   * ID of the FBISE grade subject of a subject workspace
   */
  grade_subject_id: S.optionalWith(S.String, { nullable: true }),
  /**
   * Subject code of a subject workspace: PHY, CHEM, BIO or MATH
   */
  subject_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the project was created
   */
  created_at: S.String,
}) {}

/**
 * The profile and the subject workspaces created by onboarding.
 */
export class OnboardingResultDto extends S.Class<OnboardingResultDto>(
  'OnboardingResultDto',
)({
  profile: StudentProfileDto,
  /**
   * The subject workspaces
   */
  projects: S.Array(ProjectDto),
}) {}

/**
 * How much of the syllabus the estimate is based on
 */
export class PredictedGradeDtoConfidence extends S.Literal(
  'low',
  'medium',
  'high',
) {}

/**
 * An estimate, not a result: based only on the SLOs practised so far.
 */
export class PredictedGradeDto extends S.Class<PredictedGradeDto>(
  'PredictedGradeDto',
)({
  /**
   * Estimated percentage in the theory paper
   */
  percent: S.Int,
  /**
   * IBCC grade band, e.g. B+
   */
  grade: S.String,
  /**
   * Band descriptor, e.g. Very Good
   */
  descriptor: S.String,
  /**
   * Share of the examined syllabus (by teaching time) practised, 0..1
   */
  coverage: S.Number,
  /**
   * How much of the syllabus the estimate is based on
   */
  confidence: PredictedGradeDtoConfidence,
}) {}

export class DomainProgressDto extends S.Class<DomainProgressDto>(
  'DomainProgressDto',
)({
  /**
   * Domain code, e.g. B
   */
  code: S.String,
  /**
   * Domain name, e.g. Mechanics
   */
  name: S.String,
  /**
   * Examined (summative) SLOs
   */
  examined_count: S.Int,
  /**
   * Examined SLOs practised at least once
   */
  practised_count: S.Int,
  /**
   * Average mastery of practised SLOs
   */
  mastery: S.optionalWith(S.Number, { nullable: true }),
}) {}

export class ProgressSloDto extends S.Class<ProgressSloDto>('ProgressSloDto')({
  /**
   * FBISE SLO code
   */
  code: S.String,
  /**
   * SLO text
   */
  description: S.String,
  /**
   * Domain code
   */
  domain_code: S.String,
  /**
   * Mastery 0..1, null if not practised
   */
  mastery: S.optionalWith(S.Number, { nullable: true }),
  /**
   * Practice answers recorded
   */
  attempts: S.optionalWith(S.Int, {
    nullable: true,
    default: () => 0 as const,
  }),
}) {}

export class SubjectProgressDto extends S.Class<SubjectProgressDto>(
  'SubjectProgressDto',
)({
  /**
   * ID of the subject workspace
   */
  project_id: S.String,
  /**
   * ID of the grade subject
   */
  grade_subject_id: S.String,
  /**
   * PHY, CHEM, BIO or MATH
   */
  subject_code: S.String,
  /**
   * Workspace name, e.g. Physics XI
   */
  name: S.String,
  /**
   * False while the SLO map is coming soon
   */
  has_slos: S.Boolean,
  /**
   * Examined (summative) SLOs
   */
  examined_count: S.optionalWith(S.Int, {
    nullable: true,
    default: () => 0 as const,
  }),
  /**
   * Examined SLOs practised at least once
   */
  practised_count: S.optionalWith(S.Int, {
    nullable: true,
    default: () => 0 as const,
  }),
  /**
   * Average mastery of practised SLOs
   */
  mastery: S.optionalWith(S.Number, { nullable: true }),
  /**
   * Estimated grade band
   */
  predicted: S.optionalWith(PredictedGradeDto, { nullable: true }),
  domains: S.optionalWith(S.Array(DomainProgressDto), { nullable: true }),
  /**
   * Practised SLOs with the lowest mastery
   */
  weakest: S.optionalWith(S.Array(ProgressSloDto), { nullable: true }),
  /**
   * Examined SLOs not practised yet, largest first
   */
  suggested: S.optionalWith(S.Array(ProgressSloDto), { nullable: true }),
}) {}

export class ProgressDto extends S.Class<ProgressDto>('ProgressDto')({
  subjects: S.Array(SubjectProgressDto),
}) {}

export class ListGradeSubjectsApiV1CurriculumGradeSubjectsGetParams extends S.Struct(
  {
    /**
     * Only this grade (11 or 12)
     */
    grade: S.optionalWith(S.Int, { nullable: true }),
  },
) {}

/**
 * available once the SLOs are loaded
 */
export class GradeSubjectDtoStatus extends S.Literal(
  'available',
  'coming_soon',
) {}

/**
 * A subject in one grade, e.g. Physics XI.
 */
export class GradeSubjectDto extends S.Class<GradeSubjectDto>(
  'GradeSubjectDto',
)({
  /**
   * Unique ID of the grade subject
   */
  id: S.String,
  /**
   * Subject code: PHY, CHEM, BIO or MATH
   */
  subject_code: S.String,
  /**
   * Subject name, e.g. Physics
   */
  subject_name: S.String,
  /**
   * Grade: 11 (HSSC-I) or 12 (HSSC-II)
   */
  grade: S.Int,
  /**
   * FBISE scheme of studies, e.g. ISS-2024
   */
  scheme: S.String,
  /**
   * Curriculum, e.g. NCP 2022-23
   */
  curriculum: S.optionalWith(S.String, { nullable: true }),
  /**
   * FBISE Assessment Framework the SLOs come from
   */
  source_url: S.optionalWith(S.String, { nullable: true }),
  /**
   * available once the SLOs are loaded
   */
  status: GradeSubjectDtoStatus,
  /**
   * Number of SLOs
   */
  slo_count: S.optionalWith(S.Int, {
    nullable: true,
    default: () => 0 as const,
  }),
}) {}

export class ListGradeSubjectsApiV1CurriculumGradeSubjectsGet200 extends S.Array(
  GradeSubjectDto,
) {}

/**
 * summative: examined in the annual exam; formative: classroom only; practical: assessed in the practical exam
 */
export class SloDtoAssessmentForm extends S.Literal(
  'summative',
  'formative',
  'practical',
  'unknown',
) {}

/**
 * A Student Learning Outcome with the student's progress on it.
 */
export class SloDto extends S.Class<SloDto>('SloDto')({
  /**
   * Unique ID of the SLO
   */
  id: S.String,
  /**
   * FBISE SLO code, e.g. P-11-B-05
   */
  code: S.String,
  /**
   * ID of the grade subject
   */
  grade_subject_id: S.String,
  /**
   * Domain code, e.g. B
   */
  domain_code: S.String,
  /**
   * Domain name, e.g. Mechanics
   */
  domain_name: S.String,
  /**
   * Content area, e.g. Vectors
   */
  content_area: S.optionalWith(S.String, { nullable: true }),
  /**
   * SLO text as published by FBISE
   */
  description: S.String,
  /**
   * summative: examined in the annual exam; formative: classroom only; practical: assessed in the practical exam
   */
  assessment_form: SloDtoAssessmentForm,
  /**
   * Knowledge, Understanding, Application
   */
  cognitive_levels: S.optionalWith(S.Array(S.Literal('K', 'U', 'A')), {
    nullable: true,
  }),
  /**
   * Teaching periods (40 minutes each)
   */
  periods: S.optionalWith(S.Int, { nullable: true }),
  /**
   * Practice answers recorded for this SLO
   */
  attempts: S.optionalWith(S.Int, {
    nullable: true,
    default: () => 0 as const,
  }),
  /**
   * Estimated mastery 0..1, null before any practice
   */
  mastery: S.optionalWith(S.Number, { nullable: true }),
}) {}

/**
 * A curriculum domain with its SLOs.
 */
export class DomainDto extends S.Class<DomainDto>('DomainDto')({
  /**
   * Domain code, e.g. B
   */
  code: S.String,
  /**
   * Domain name, e.g. Mechanics
   */
  name: S.String,
  /**
   * Number of SLOs
   */
  slo_count: S.Int,
  /**
   * Number of summative (examined) SLOs
   */
  examined_count: S.Int,
  /**
   * Average mastery of the practised SLOs, 0..1
   */
  mastery: S.optionalWith(S.Number, { nullable: true }),
  slos: S.optionalWith(S.Array(SloDto), { nullable: true }),
}) {}

/**
 * The syllabus map of one grade subject.
 */
export class CurriculumTreeDto extends S.Class<CurriculumTreeDto>(
  'CurriculumTreeDto',
)({
  grade_subject: GradeSubjectDto,
  domains: S.Array(DomainDto),
}) {}

export class GetSloApiV1CurriculumSlosCodeGetParams extends S.Struct({
  /**
   * Limit to one grade subject
   */
  grade_subject_id: S.optionalWith(S.String, { nullable: true }),
}) {}

export class SloExplainerDto extends S.Class<SloExplainerDto>(
  'SloExplainerDto',
)({
  /**
   * FBISE SLO code
   */
  slo_code: S.String,
  /**
   * Explainer title
   */
  title: S.String,
  /**
   * Explainer in Markdown with LaTeX
   */
  content: S.String,
  /**
   * True once a subject teacher approved it
   */
  reviewed: S.Boolean,
}) {}

export class SloExplainerStateDto extends S.Class<SloExplainerStateDto>(
  'SloExplainerStateDto',
)({
  /**
   * The explainer, or null if none has been written yet
   */
  explainer: S.optionalWith(SloExplainerDto, { nullable: true }),
}) {}

export class ListProjectsApiV1ProjectsGet200 extends S.Array(ProjectDto) {}

export class ProjectCreate extends S.Class<ProjectCreate>('ProjectCreate')({
  /**
   * Name of the project
   */
  name: S.String,
  /**
   * Description of the project
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * Language code for the project
   */
  language_code: S.optionalWith(S.String, {
    nullable: true,
    default: () => 'en' as const,
  }),
}) {}

export class ProjectUpdate extends S.Class<ProjectUpdate>('ProjectUpdate')({
  /**
   * Name of the project
   */
  name: S.optionalWith(S.String, { nullable: true }),
  /**
   * Description of the project
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * Language code for the project
   */
  language_code: S.optionalWith(S.String, { nullable: true }),
}) {}

export class BodyUploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost extends S.Class<BodyUploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost>(
  'BodyUploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost',
)({
  files: S.Array(S.instanceOf(globalThis.Blob)),
}) {}

export class UploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost201 extends S.Struct(
  {},
) {}

/**
 * Document processing status enum.
 */
export class DocumentStatus extends S.Literal(
  'uploaded',
  'processing',
  'processed',
  'indexed',
  'failed',
) {}

export class DocumentDto extends S.Class<DocumentDto>('DocumentDto')({
  /**
   * Unique ID of the document
   */
  id: S.String,
  /**
   * ID of the document owner
   */
  owner_id: S.String,
  /**
   * ID of the project the document belongs to
   */
  project_id: S.optionalWith(S.String, { nullable: true }),
  /**
   * Name of the document file
   */
  file_name: S.String,
  /**
   * File extension (pdf, docx, txt, etc.)
   */
  file_type: S.String,
  /**
   * File size in bytes
   */
  file_size: S.Int.pipe(S.greaterThan(0)),
  /**
   * Document processing status: uploaded, processing, processed, failed, indexed
   */
  status: DocumentStatus,
  /**
   * Auto-generated summary of the document
   */
  summary: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the document was uploaded
   */
  uploaded_at: S.String,
  /**
   * Date and time the document was processed
   */
  processed_at: S.optionalWith(S.String, { nullable: true }),
}) {}

export class ListDocumentsApiV1ProjectsProjectIdDocumentsGet200 extends S.Array(
  DocumentDto,
) {}

export class DocumentCreate extends S.Class<DocumentCreate>('DocumentCreate')({
  /**
   * Name of the document file
   */
  file_name: S.String,
  /**
   * File extension (pdf, docx, txt, etc.)
   */
  file_type: S.String,
  /**
   * File size in bytes
   */
  file_size: S.Int.pipe(S.greaterThan(0)),
  /**
   * Auto-generated summary of the document
   */
  summary: S.optionalWith(S.String, { nullable: true }),
}) {}

export class DocumentUpdate extends S.Class<DocumentUpdate>('DocumentUpdate')({
  /**
   * Name of the document file
   */
  file_name: S.optionalWith(S.String, { nullable: true }),
  /**
   * Auto-generated summary of the document
   */
  summary: S.optionalWith(S.String, { nullable: true }),
}) {}

export class DocumentPreviewDto extends S.Class<DocumentPreviewDto>(
  'DocumentPreviewDto',
)({
  /**
   * URL of the document preview
   */
  url: S.String,
}) {}

export class ChatDto extends S.Class<ChatDto>('ChatDto')({
  /**
   * Unique ID of the chat
   */
  id: S.String,
  /**
   * ID of the project this chat belongs to
   */
  project_id: S.String,
  /**
   * ID of the user who created the chat
   */
  user_id: S.String,
  /**
   * Title of the chat
   */
  title: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the chat was created
   */
  created_at: S.String,
  /**
   * Date and time the chat was updated
   */
  updated_at: S.String,
  /**
   * Content preview of the last message
   */
  last_message_content: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time of the last message
   */
  last_message_at: S.optionalWith(S.String, { nullable: true }),
}) {}

export class ListChatsApiV1ProjectsProjectIdChatsGet200 extends S.Array(
  ChatDto,
) {}

export class ChatCreate extends S.Class<ChatCreate>('ChatCreate')({
  /**
   * Title of the chat
   */
  title: S.optionalWith(S.String, { nullable: true }),
}) {}

export class TextPartDto extends S.Class<TextPartDto>('TextPartDto')({
  /**
   * Unique ID of the part (for streaming tracking)
   */
  id: S.optionalWith(S.String, { nullable: true }),
  /**
   * Order of the part within the message
   */
  order: S.optionalWith(S.Int, { nullable: true, default: () => 0 as const }),
  type: S.optionalWith(S.Literal('text'), {
    nullable: true,
    default: () => 'text' as const,
  }),
  /**
   * Text content of the message part
   */
  text_content: S.String,
}) {}

export class FilePartDto extends S.Class<FilePartDto>('FilePartDto')({
  /**
   * Unique ID of the part (for streaming tracking)
   */
  id: S.optionalWith(S.String, { nullable: true }),
  /**
   * Order of the part within the message
   */
  order: S.optionalWith(S.Int, { nullable: true, default: () => 0 as const }),
  type: S.optionalWith(S.Literal('file'), {
    nullable: true,
    default: () => 'file' as const,
  }),
  /**
   * Original name of the uploaded file
   */
  file_name: S.String,
  /**
   * MIME type of the uploaded file
   */
  file_type: S.String,
  /**
   * URL to access the uploaded file
   */
  file_url: S.String,
}) {}

/**
 * Current state of the tool call
 */
export class ToolCallPartDtoToolState extends S.Literal(
  'input-streaming',
  'input-available',
  'output-available',
  'output-error',
) {}

export class ToolCallPartDto extends S.Class<ToolCallPartDto>(
  'ToolCallPartDto',
)({
  /**
   * Unique ID of the part (for streaming tracking)
   */
  id: S.optionalWith(S.String, { nullable: true }),
  /**
   * Order of the part within the message
   */
  order: S.optionalWith(S.Int, { nullable: true, default: () => 0 as const }),
  type: S.optionalWith(S.Literal('tool_call'), {
    nullable: true,
    default: () => 'tool_call' as const,
  }),
  /**
   * Unique ID of the tool call
   */
  tool_call_id: S.String,
  /**
   * Name of the tool being called
   */
  tool_name: S.String,
  /**
   * Input parameters for the tool
   */
  tool_input: S.optionalWith(S.Record({ key: S.String, value: S.Unknown }), {
    nullable: true,
  }),
  /**
   * Output result from the tool
   */
  tool_output: S.optionalWith(
    S.Union(S.Record({ key: S.String, value: S.Unknown }), S.String),
    { nullable: true },
  ),
  /**
   * Current state of the tool call
   */
  tool_state: ToolCallPartDtoToolState,
}) {}

export class SourceDocumentPartDto extends S.Class<SourceDocumentPartDto>(
  'SourceDocumentPartDto',
)({
  /**
   * Unique ID of the part (for streaming tracking)
   */
  id: S.optionalWith(S.String, { nullable: true }),
  /**
   * Order of the part within the message
   */
  order: S.optionalWith(S.Int, { nullable: true, default: () => 0 as const }),
  type: S.optionalWith(S.Literal('source-document'), {
    nullable: true,
    default: () => 'source-document' as const,
  }),
  /**
   * Unique identifier for the source document
   */
  source_id: S.String,
  /**
   * MIME type of the source document
   */
  media_type: S.String,
  /**
   * Title of the source document
   */
  title: S.String,
  /**
   * Filename of the source document
   */
  filename: S.optionalWith(S.String, { nullable: true }),
  /**
   * Additional metadata from the provider
   */
  provider_metadata: S.optionalWith(
    S.Record({ key: S.String, value: S.Unknown }),
    { nullable: true },
  ),
}) {}

export class ChatMessageDto extends S.Class<ChatMessageDto>('ChatMessageDto')({
  /**
   * Unique ID of the message
   */
  id: S.String,
  /**
   * ID of the chat this message belongs to
   */
  chat_id: S.String,
  /**
   * Role of the message sender
   */
  role: S.String,
  /**
   * Date and time the message was created
   */
  created_at: S.String,
  /**
   * List of parts composing the message
   */
  parts: S.optionalWith(
    S.Array(
      S.Union(TextPartDto, FilePartDto, ToolCallPartDto, SourceDocumentPartDto),
    ),
    { nullable: true },
  ),
}) {}

/**
 * Chat DTO with messages and parts included.
 */
export class ChatDetailDto extends S.Class<ChatDetailDto>('ChatDetailDto')({
  /**
   * Unique ID of the chat
   */
  id: S.String,
  /**
   * ID of the project this chat belongs to
   */
  project_id: S.String,
  /**
   * ID of the user who created the chat
   */
  user_id: S.String,
  /**
   * Title of the chat
   */
  title: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the chat was created
   */
  created_at: S.String,
  /**
   * Date and time the chat was updated
   */
  updated_at: S.String,
  /**
   * Content preview of the last message
   */
  last_message_content: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time of the last message
   */
  last_message_at: S.optionalWith(S.String, { nullable: true }),
  /**
   * List of messages in the chat
   */
  messages: S.optionalWith(S.Array(ChatMessageDto), { nullable: true }),
}) {}

export class ChatUpdate extends S.Class<ChatUpdate>('ChatUpdate')({
  /**
   * Title of the chat
   */
  title: S.optionalWith(S.String, { nullable: true }),
}) {}

export class TextPart extends S.Class<TextPart>('TextPart')({
  type: S.Literal('text'),
  text: S.String,
}) {}

export class FilePart extends S.Class<FilePart>('FilePart')({
  type: S.Literal('file'),
  mediaType: S.String,
  filename: S.optionalWith(S.String, { nullable: true }),
  url: S.String,
}) {}

export class ChatCompletionRequest extends S.Class<ChatCompletionRequest>(
  'ChatCompletionRequest',
)({
  parts: S.Array(S.Union(TextPart, FilePart)),
}) {}

export class SendStreamingMessageApiV1ProjectsProjectIdChatsChatIdMessagesStreamPost200 extends S.Struct(
  {},
) {}

export class NoteDto extends S.Class<NoteDto>('NoteDto')({
  /**
   * Unique ID of the note
   */
  id: S.String,
  /**
   * ID of the project the note belongs to
   */
  project_id: S.String,
  /**
   * Title of the note
   */
  title: S.String,
  /**
   * Description of the note
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * Content of the note
   */
  content: S.String,
  /**
   * Date and time the note was created
   */
  created_at: S.String,
  /**
   * Date and time the note was updated
   */
  updated_at: S.String,
}) {}

export class ListNotesApiV1ProjectsProjectIdNotesGet200 extends S.Array(
  NoteDto,
) {}

export class NoteCreate extends S.Class<NoteCreate>('NoteCreate')({
  /**
   * Title of the note
   */
  title: S.String,
  /**
   * Content of the note
   */
  content: S.String,
  /**
   * Description of the note
   */
  description: S.optionalWith(S.String, { nullable: true }),
}) {}

export class NoteUpdate extends S.Class<NoteUpdate>('NoteUpdate')({
  /**
   * Title of the note
   */
  title: S.optionalWith(S.String, { nullable: true }),
  /**
   * Content of the note
   */
  content: S.optionalWith(S.String, { nullable: true }),
  /**
   * Description of the note
   */
  description: S.optionalWith(S.String, { nullable: true }),
}) {}

export class GenerateRequest extends S.Class<GenerateRequest>(
  'GenerateRequest',
)({
  /**
   * Topic for generation
   */
  topic: S.optionalWith(S.String, { nullable: true }),
  /**
   * Custom instructions for generation
   */
  custom_instructions: S.optionalWith(S.String, { nullable: true }),
  /**
   * Number of items to generate (for flashcards/quizzes)
   */
  count: S.optionalWith(S.Int, { nullable: true }),
  /**
   * Difficulty level (for flashcards/quizzes)
   */
  difficulty: S.optionalWith(S.String, { nullable: true }),
  /**
   * FBISE SLO to target, e.g. P-11-B-05 (for flashcards/quizzes)
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
}) {}

export class GenerateNoteStreamApiV1ProjectsProjectIdNotesNoteIdGenerateStreamPost200 extends S.Struct(
  {},
) {}

export class QuizDto extends S.Class<QuizDto>('QuizDto')({
  /**
   * Unique ID of the quiz
   */
  id: S.String,
  /**
   * ID of the project the quiz belongs to
   */
  project_id: S.String,
  /**
   * Name of the quiz
   */
  name: S.String,
  /**
   * Description of the quiz
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * FBISE SLO code, e.g. P-11-B-05
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the quiz was created
   */
  created_at: S.String,
  /**
   * Date and time the quiz was updated
   */
  updated_at: S.String,
}) {}

export class ListQuizzesApiV1ProjectsProjectIdQuizzesGet200 extends S.Array(
  QuizDto,
) {}

export class QuizCreate extends S.Class<QuizCreate>('QuizCreate')({
  /**
   * Name of the quiz
   */
  name: S.String,
  /**
   * Description of the quiz
   */
  description: S.optionalWith(S.String, { nullable: true }),
}) {}

export class QuizUpdate extends S.Class<QuizUpdate>('QuizUpdate')({
  /**
   * Name of the quiz
   */
  name: S.optionalWith(S.String, { nullable: true }),
  /**
   * Description of the quiz
   */
  description: S.optionalWith(S.String, { nullable: true }),
}) {}

export class GenerateQuizStreamApiV1ProjectsProjectIdQuizzesQuizIdGenerateStreamPost200 extends S.Struct(
  {},
) {}

/**
 * Quiz question data transfer object.
 */
export class QuizQuestionDto extends S.Class<QuizQuestionDto>(
  'QuizQuestionDto',
)({
  /**
   * Unique ID of the quiz question
   */
  id: S.String,
  /**
   * ID of the quiz this question belongs to
   */
  quiz_id: S.String,
  /**
   * ID of the project
   */
  project_id: S.String,
  /**
   * The quiz question text
   */
  question_text: S.String,
  /**
   * Option A
   */
  option_a: S.String,
  /**
   * Option B
   */
  option_b: S.String,
  /**
   * Option C
   */
  option_c: S.String,
  /**
   * Option D
   */
  option_d: S.String,
  /**
   * Correct option: a, b, c, or d
   */
  correct_option: S.String,
  /**
   * Explanation for the correct answer
   */
  explanation: S.optionalWith(S.String, { nullable: true }),
  /**
   * Difficulty level: easy, medium, or hard
   */
  difficulty_level: S.String,
  /**
   * Position for ordering within quiz
   */
  position: S.Int,
  /**
   * FBISE SLO code, e.g. P-11-B-05
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * Cognitive level: K, U or A
   */
  cognitive_level: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the question was created
   */
  created_at: S.String,
}) {}

export class ListQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsGet200 extends S.Array(
  QuizQuestionDto,
) {}

export class QuizQuestionCreate extends S.Class<QuizQuestionCreate>(
  'QuizQuestionCreate',
)({
  /**
   * The quiz question text
   */
  question_text: S.String,
  /**
   * Option A
   */
  option_a: S.String,
  /**
   * Option B
   */
  option_b: S.String,
  /**
   * Option C
   */
  option_c: S.String,
  /**
   * Option D
   */
  option_d: S.String,
  /**
   * Correct option: a, b, c, or d
   */
  correct_option: S.String,
  /**
   * Explanation for the correct answer
   */
  explanation: S.optionalWith(S.String, { nullable: true }),
  /**
   * Difficulty level (easy, medium, hard)
   */
  difficulty_level: S.optionalWith(S.String, {
    nullable: true,
    default: () => 'medium' as const,
  }),
  /**
   * Position for ordering within the quiz
   */
  position: S.optionalWith(S.Int, { nullable: true }),
}) {}

export class QuizQuestionUpdate extends S.Class<QuizQuestionUpdate>(
  'QuizQuestionUpdate',
)({
  /**
   * The quiz question text
   */
  question_text: S.optionalWith(S.String, { nullable: true }),
  /**
   * Option A
   */
  option_a: S.optionalWith(S.String, { nullable: true }),
  /**
   * Option B
   */
  option_b: S.optionalWith(S.String, { nullable: true }),
  /**
   * Option C
   */
  option_c: S.optionalWith(S.String, { nullable: true }),
  /**
   * Option D
   */
  option_d: S.optionalWith(S.String, { nullable: true }),
  /**
   * Correct option: a, b, c, or d
   */
  correct_option: S.optionalWith(S.String, { nullable: true }),
  /**
   * Explanation for the correct answer
   */
  explanation: S.optionalWith(S.String, { nullable: true }),
  /**
   * Difficulty level (easy, medium, hard)
   */
  difficulty_level: S.optionalWith(S.String, { nullable: true }),
  /**
   * Position for ordering within the quiz
   */
  position: S.optionalWith(S.Int, { nullable: true }),
}) {}

export class QuizQuestionReorder extends S.Class<QuizQuestionReorder>(
  'QuizQuestionReorder',
)({
  /**
   * List of question IDs in the desired order
   */
  question_ids: S.Array(S.String),
}) {}

export class ReorderQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsReorderPatch200 extends S.Array(
  QuizQuestionDto,
) {}

export class QuizAnswer extends S.Class<QuizAnswer>('QuizAnswer')({
  /**
   * ID of the quiz question
   */
  question_id: S.String,
  /**
   * Chosen option: a, b, c or d (null if skipped)
   */
  option: S.optionalWith(S.String, { nullable: true }),
}) {}

export class QuizAttemptCreate extends S.Class<QuizAttemptCreate>(
  'QuizAttemptCreate',
)({
  /**
   * One answer per question
   */
  answers: S.Array(QuizAnswer).pipe(S.maxItems(100)),
}) {}

export class QuizAnswerResultDto extends S.Class<QuizAnswerResultDto>(
  'QuizAnswerResultDto',
)({
  /**
   * ID of the quiz question
   */
  question_id: S.String,
  /**
   * Option the student chose: a, b, c or d
   */
  chosen: S.optionalWith(S.String, { nullable: true }),
  /**
   * The correct option
   */
  correct_option: S.String,
  /**
   * Whether the student was right
   */
  is_correct: S.Boolean,
}) {}

/**
 * A finished attempt at a quiz.
 */
export class QuizAttemptDto extends S.Class<QuizAttemptDto>('QuizAttemptDto')({
  /**
   * Unique ID of the attempt
   */
  id: S.String,
  /**
   * ID of the quiz
   */
  quiz_id: S.String,
  /**
   * Attempt number at this quiz: 1 for the first try
   */
  number: S.optionalWith(S.Int, { nullable: true, default: () => 1 as const }),
  /**
   * Number of correct answers
   */
  score: S.Number,
  /**
   * Number of questions
   */
  max_score: S.Number,
  /**
   * Result per question
   */
  answers: S.Array(QuizAnswerResultDto),
  /**
   * When the attempt was submitted
   */
  created_at: S.String,
}) {}

/**
 * The score of one attempt, for a list of earlier attempts.
 */
export class AttemptSummaryDto extends S.Class<AttemptSummaryDto>(
  'AttemptSummaryDto',
)({
  /**
   * Unique ID of the attempt
   */
  id: S.String,
  /**
   * Attempt number: 1 for the first try
   */
  number: S.Int,
  /**
   * Marks or correct answers
   */
  score: S.Number,
  /**
   * Marks available
   */
  max_score: S.Number,
  /**
   * When the attempt was submitted
   */
  created_at: S.String,
}) {}

export class QuizAttemptStateDto extends S.Class<QuizAttemptStateDto>(
  'QuizAttemptStateDto',
)({
  /**
   * The latest attempt, or null if the quiz was not attempted yet
   */
  attempt: S.optionalWith(QuizAttemptDto, { nullable: true }),
  /**
   * Every attempt at this quiz, first to last
   */
  history: S.optionalWith(S.Array(AttemptSummaryDto), { nullable: true }),
}) {}

export class ListSrqsApiV1ProjectsProjectIdSrqGetParams extends S.Struct({
  /**
   * Only questions for this SLO
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
}) {}

/**
 * A short-response question; the rubric and model answer are shown after marking.
 */
export class SrqQuestionDto extends S.Class<SrqQuestionDto>('SrqQuestionDto')({
  /**
   * Unique ID of the question
   */
  id: S.String,
  /**
   * ID of the project
   */
  project_id: S.String,
  /**
   * FBISE SLO code, e.g. P-11-B-05
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * Question text (Markdown with LaTeX)
   */
  question: S.String,
  /**
   * Total marks
   */
  marks: S.Int,
  /**
   * K, U or A
   */
  cognitive_level: S.optionalWith(S.String, { nullable: true }),
  /**
   * When the question was created
   */
  created_at: S.String,
}) {}

export class ListSrqsApiV1ProjectsProjectIdSrqGet200 extends S.Array(
  SrqQuestionDto,
) {}

export class SrqCreate extends S.Class<SrqCreate>('SrqCreate')({
  /**
   * FBISE SLO code, e.g. P-11-B-05
   */
  slo_code: S.String.pipe(S.maxLength(32)),
}) {}

export class SrqPointResultDto extends S.Class<SrqPointResultDto>(
  'SrqPointResultDto',
)({
  /**
   * The rubric point
   */
  point: S.String,
  /**
   * Marks available for this point
   */
  marks: S.Number,
  /**
   * Marks awarded
   */
  awarded: S.Number,
  /**
   * What the student wrote or missed
   */
  comment: S.optionalWith(S.String, {
    nullable: true,
    default: () => '' as const,
  }),
}) {}

/**
 * A marked written answer. Marks are AI-estimated.
 */
export class SrqAttemptDto extends S.Class<SrqAttemptDto>('SrqAttemptDto')({
  /**
   * Unique ID of the attempt
   */
  id: S.String,
  /**
   * ID of the question
   */
  question_id: S.String,
  /**
   * The student's answer
   */
  answer: S.String,
  /**
   * AI-estimated marks
   */
  awarded_marks: S.Number,
  /**
   * Total marks
   */
  max_marks: S.Int,
  /**
   * Marks per rubric point
   */
  points: S.Array(SrqPointResultDto),
  /**
   * How to get full marks
   */
  feedback: S.optionalWith(S.String, {
    nullable: true,
    default: () => '' as const,
  }),
  /**
   * Rubric points not fully earned
   */
  missing: S.optionalWith(S.Array(S.String), { nullable: true }),
  /**
   * A full-marks answer
   */
  model_answer: S.String,
  /**
   * When the answer was marked
   */
  created_at: S.String,
}) {}

export class SrqDetailDto extends S.Class<SrqDetailDto>('SrqDetailDto')({
  question: SrqQuestionDto,
  /**
   * The student's attempts, newest first
   */
  attempts: S.Array(SrqAttemptDto),
}) {}

export class SrqAnswer extends S.Class<SrqAnswer>('SrqAnswer')({
  /**
   * The student's written answer
   */
  answer: S.String.pipe(S.minLength(1), S.maxLength(5000)),
}) {}

export class PaperSummaryDtoLength extends S.Literal(
  'mini',
  'standard',
  'board',
  'half',
) {}

export class PaperSummaryDtoStatus extends S.Literal(
  'preparing',
  'ready',
  'submitted',
  'failed',
) {}

export class PaperSummaryDto extends S.Class<PaperSummaryDto>(
  'PaperSummaryDto',
)({
  id: S.String,
  title: S.String,
  length: PaperSummaryDtoLength,
  status: PaperSummaryDtoStatus,
  total_marks: S.Number,
  score: S.optionalWith(S.Number, { nullable: true }),
  created_at: S.String,
}) {}

export class ListPapersApiV1ProjectsProjectIdPapersGet200 extends S.Array(
  PaperSummaryDto,
) {}

/**
 * mini: 8 MCQs + 2 SRQs; standard: 12 MCQs + 4 SRQs + 1 ERQ; board / half: FBISE's new pattern (stimulus MCQs, questions with internal choice), built in the background
 */
export class PaperCreateLength extends S.Literal(
  'mini',
  'standard',
  'board',
  'half',
) {}

export class PaperCreate extends S.Class<PaperCreate>('PaperCreate')({
  /**
   * mini: 8 MCQs + 2 SRQs; standard: 12 MCQs + 4 SRQs + 1 ERQ; board / half: FBISE's new pattern (stimulus MCQs, questions with internal choice), built in the background
   */
  length: S.optionalWith(PaperCreateLength, {
    nullable: true,
    default: () => 'mini' as const,
  }),
  /**
   * A domain (e.g. Mechanics) or topic; empty for the whole syllabus
   */
  topic: S.optionalWith(S.String.pipe(S.maxLength(200)), { nullable: true }),
}) {}

/**
 * mini, standard, or the FBISE new-pattern board / half paper
 */
export class PaperDtoLength extends S.Literal(
  'mini',
  'standard',
  'board',
  'half',
) {}

/**
 * preparing (board papers), ready, submitted or failed
 */
export class PaperDtoStatus extends S.Literal(
  'preparing',
  'ready',
  'submitted',
  'failed',
) {}

/**
 * MCQ, short or long question
 */
export class PaperItemDtoType extends S.Literal('mcq', 'srq', 'erq') {}

export class PaperItemDto extends S.Class<PaperItemDto>('PaperItemDto')({
  /**
   * ID of the item within the paper (SRQ/ERQ: the question ID)
   */
  id: S.String,
  /**
   * MCQ, short or long question
   */
  type: PaperItemDtoType,
  /**
   * Marks for this item
   */
  marks: S.Number,
  /**
   * FBISE SLO the item assesses
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * K, U or A
   */
  cognitive_level: S.optionalWith(S.String, { nullable: true }),
  /**
   * Question text (Markdown with LaTeX)
   */
  question: S.String,
  /**
   * MCQ options a-d
   */
  options: S.optionalWith(S.Record({ key: S.String, value: S.Unknown }), {
    nullable: true,
  }),
  /**
   * Stimulus MCQ: the scenario it is based on
   */
  stimulus: S.optionalWith(S.String, { nullable: true }),
  /**
   * Stimulus MCQ: its set, e.g. s1
   */
  group: S.optionalWith(S.String, { nullable: true }),
  /**
   * Internal choice: the question number, e.g. B1 (answer (a) OR (b))
   */
  choice_group: S.optionalWith(S.String, { nullable: true }),
  /**
   * Internal choice: a or b
   */
  choice: S.optionalWith(S.String, { nullable: true }),
}) {}

export class PaperSectionDto extends S.Class<PaperSectionDto>(
  'PaperSectionDto',
)({
  /**
   * A, B or C
   */
  id: S.String,
  /**
   * Section title
   */
  title: S.String,
  items: S.Array(PaperItemDto),
}) {}

export class PaperSectionResultDto extends S.Class<PaperSectionResultDto>(
  'PaperSectionResultDto',
)({
  id: S.String,
  title: S.String,
  score: S.Number,
  max_score: S.Number,
}) {}

export class PaperItemResultDtoType extends S.Literal('mcq', 'srq', 'erq') {}

export class PaperItemResultDto extends S.Class<PaperItemResultDto>(
  'PaperItemResultDto',
)({
  /**
   * ID of the item
   */
  id: S.String,
  type: PaperItemResultDtoType,
  /**
   * Marks available
   */
  marks: S.Number,
  /**
   * Marks awarded (AI-estimated for written answers)
   */
  awarded: S.Number,
  /**
   * MCQ: the option chosen
   */
  chosen: S.optionalWith(S.String, { nullable: true }),
  /**
   * MCQ: the correct option
   */
  correct_option: S.optionalWith(S.String, { nullable: true }),
  /**
   * MCQ: why the answer is right
   */
  explanation: S.optionalWith(S.String, { nullable: true }),
  /**
   * Written: the student's answer
   */
  answer: S.optionalWith(S.String, { nullable: true }),
  /**
   * Written: marks per rubric point
   */
  marking: S.optionalWith(SrqAttemptDto, { nullable: true }),
  /**
   * Written: a full-marks answer
   */
  model_answer: S.optionalWith(S.String, { nullable: true }),
}) {}

export class PaperResultDto extends S.Class<PaperResultDto>('PaperResultDto')({
  /**
   * Total marks awarded
   */
  score: S.Number,
  /**
   * Total marks
   */
  max_score: S.Number,
  /**
   * Score as a percentage
   */
  percent: S.Int,
  /**
   * IBCC grade band for this paper
   */
  grade: S.String,
  /**
   * Band descriptor
   */
  descriptor: S.String,
  sections: S.Array(PaperSectionResultDto),
  items: S.Array(PaperItemResultDto),
}) {}

/**
 * A practice paper; answers and marking appear once it is submitted.
 */
export class PaperDto extends S.Class<PaperDto>('PaperDto')({
  /**
   * Unique ID of the paper
   */
  id: S.String,
  /**
   * ID of the subject workspace
   */
  project_id: S.String,
  /**
   * Paper title
   */
  title: S.String,
  /**
   * mini, standard, or the FBISE new-pattern board / half paper
   */
  length: PaperDtoLength,
  /**
   * Time allowed
   */
  time_limit_minutes: S.Int,
  /**
   * Total marks
   */
  total_marks: S.Number,
  /**
   * preparing (board papers), ready, submitted or failed
   */
  status: PaperDtoStatus,
  sections: S.Array(PaperSectionDto),
  /**
   * Saved answers by item ID
   */
  answers: S.optionalWith(S.Record({ key: S.String, value: S.Unknown }), {
    nullable: true,
  }),
  /**
   * Marks, once submitted
   */
  result: S.optionalWith(PaperResultDto, { nullable: true }),
  created_at: S.String,
  submitted_at: S.optionalWith(S.String, { nullable: true }),
}) {}

export class PaperAnswers extends S.Class<PaperAnswers>('PaperAnswers')({
  /**
   * Answers by item ID (MCQ: a-d; written: text)
   */
  answers: S.optionalWith(S.Record({ key: S.String, value: S.Unknown }), {
    nullable: true,
  }),
}) {}

/**
 * One finished attempt in the student's practice history.
 */
export class PracticeHistoryItemDto extends S.Class<PracticeHistoryItemDto>(
  'PracticeHistoryItemDto',
)({
  /**
   * Unique ID of the attempt
   */
  id: S.String,
  /**
   * quiz, flashcards or paper
   */
  kind: S.String,
  /**
   * ID of the quiz, flashcard set or paper
   */
  ref_id: S.String,
  /**
   * Name of the quiz, flashcard set or paper
   */
  title: S.String,
  /**
   * Attempt number at this item: 1 for the first try
   */
  number: S.Int,
  /**
   * Marks, correct answers or cards known
   */
  score: S.Number,
  /**
   * Marks, questions or cards
   */
  max_score: S.Number,
  /**
   * When the attempt was submitted
   */
  created_at: S.String,
}) {}

export class ListPracticeHistoryApiV1ProjectsProjectIdAttemptsGet200 extends S.Array(
  PracticeHistoryItemDto,
) {}

export class ReviewerStateDto extends S.Class<ReviewerStateDto>(
  'ReviewerStateDto',
)({
  /**
   * True if this user may review content
   */
  is_reviewer: S.Boolean,
}) {}

export class ListReviewItemsApiV1ReviewItemsGetParams extends S.Struct({
  /**
   * Grade subject to review
   */
  grade_subject_id: S.String,
  /**
   * Only this domain, e.g. B
   */
  domain_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * explainer, mcq or srq
   */
  kind: S.optionalWith(S.String, { nullable: true }),
  /**
   * draft, approved or rejected
   */
  review_status: S.optionalWith(S.String, { nullable: true }),
  /**
   * Only this SLO
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
}) {}

/**
 * Type of item
 */
export class ContentItemDtoKind extends S.Literal('explainer', 'mcq', 'srq') {}

/**
 * Review status
 */
export class ContentItemDtoReviewStatus extends S.Literal(
  'draft',
  'approved',
  'rejected',
) {}

/**
 * A shared content item for one SLO, as shown in the review queue.
 */
export class ContentItemDto extends S.Class<ContentItemDto>('ContentItemDto')({
  /**
   * Unique ID of the item
   */
  id: S.String,
  /**
   * ID of the grade subject
   */
  grade_subject_id: S.String,
  /**
   * FBISE SLO code
   */
  slo_code: S.String,
  /**
   * SLO text
   */
  slo_description: S.optionalWith(S.String, {
    nullable: true,
    default: () => '' as const,
  }),
  /**
   * Type of item
   */
  kind: ContentItemDtoKind,
  /**
   * explainer: {title, content}; mcq: {question_text, option_a..option_d, correct_option, explanation, cognitive_level}; srq: {question, marks, model_answer, rubric}
   */
  payload: S.Record({ key: S.String, value: S.Unknown }),
  /**
   * Review status
   */
  review_status: ContentItemDtoReviewStatus,
  /**
   * Reviewer's note
   */
  review_note: S.optionalWith(S.String, { nullable: true }),
  /**
   * Reviewer's email
   */
  reviewed_by: S.optionalWith(S.String, { nullable: true }),
  /**
   * When the item was generated
   */
  created_at: S.String,
}) {}

export class ListReviewItemsApiV1ReviewItemsGet200 extends S.Array(
  ContentItemDto,
) {}

export class ReviewSummaryApiV1ReviewSummaryGetParams extends S.Struct({
  /**
   * Grade subject
   */
  grade_subject_id: S.String,
}) {}

export class ContentSummaryDto extends S.Class<ContentSummaryDto>(
  'ContentSummaryDto',
)({
  /**
   * explainer, mcq or srq
   */
  kind: S.String,
  /**
   * draft, approved or rejected
   */
  review_status: S.String,
  /**
   * Number of items
   */
  count: S.Int,
}) {}

export class ReviewSummaryApiV1ReviewSummaryGet200 extends S.Array(
  ContentSummaryDto,
) {}

/**
 * New review status
 */
export class ContentReviewReviewStatus extends S.Literal(
  'draft',
  'approved',
  'rejected',
) {}

export class ContentReview extends S.Class<ContentReview>('ContentReview')({
  /**
   * New review status
   */
  review_status: ContentReviewReviewStatus,
  /**
   * What is wrong or should change
   */
  review_note: S.optionalWith(S.String.pipe(S.maxLength(2000)), {
    nullable: true,
  }),
}) {}

export class FlashcardGroupDto extends S.Class<FlashcardGroupDto>(
  'FlashcardGroupDto',
)({
  /**
   * Unique ID of the flashcard group
   */
  id: S.String,
  /**
   * ID of the project the flashcard group belongs to
   */
  project_id: S.String,
  /**
   * Name of the flashcard group
   */
  name: S.String,
  /**
   * Description of the flashcard group
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * FBISE SLO code, e.g. P-11-B-05
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the flashcard group was created
   */
  created_at: S.String,
  /**
   * Date and time the flashcard group was updated
   */
  updated_at: S.String,
}) {}

export class ListFlashcardGroupsApiV1ProjectsProjectIdFlashcardGroupsGet200 extends S.Array(
  FlashcardGroupDto,
) {}

export class FlashcardGroupCreate extends S.Class<FlashcardGroupCreate>(
  'FlashcardGroupCreate',
)({
  /**
   * Name of the flashcard group
   */
  name: S.String,
  /**
   * Description of the flashcard group
   */
  description: S.optionalWith(S.String, { nullable: true }),
}) {}

export class FlashcardGroupUpdate extends S.Class<FlashcardGroupUpdate>(
  'FlashcardGroupUpdate',
)({
  /**
   * Name of the flashcard group
   */
  name: S.optionalWith(S.String, { nullable: true }),
  /**
   * Description of the flashcard group
   */
  description: S.optionalWith(S.String, { nullable: true }),
}) {}

export class GenerateFlashcardsStreamApiV1ProjectsProjectIdFlashcardGroupsGroupIdGenerateStreamPost200 extends S.Struct(
  {},
) {}

export class FlashcardDto extends S.Class<FlashcardDto>('FlashcardDto')({
  /**
   * Unique ID of the flashcard
   */
  id: S.String,
  /**
   * ID of the flashcard group
   */
  group_id: S.String,
  /**
   * ID of the project the flashcard belongs to
   */
  project_id: S.String,
  /**
   * Question of the flashcard
   */
  question: S.String,
  /**
   * Answer of the flashcard
   */
  answer: S.String,
  /**
   * Difficulty level of the flashcard
   */
  difficulty_level: S.String,
  /**
   * Position of the flashcard within the group
   */
  position: S.Int,
  /**
   * FBISE SLO code, e.g. P-11-B-05
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the flashcard was created
   */
  created_at: S.String,
}) {}

export class ListFlashcardsApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsGet200 extends S.Array(
  FlashcardDto,
) {}

export class FlashcardCreate extends S.Class<FlashcardCreate>(
  'FlashcardCreate',
)({
  /**
   * Question of the flashcard
   */
  question: S.String,
  /**
   * Answer of the flashcard
   */
  answer: S.String,
  /**
   * Difficulty level (easy, medium, hard)
   */
  difficulty_level: S.optionalWith(S.String, {
    nullable: true,
    default: () => 'medium' as const,
  }),
  /**
   * Position for ordering within the group
   */
  position: S.optionalWith(S.Int, { nullable: true }),
}) {}

export class FlashcardUpdate extends S.Class<FlashcardUpdate>(
  'FlashcardUpdate',
)({
  /**
   * Question of the flashcard
   */
  question: S.optionalWith(S.String, { nullable: true }),
  /**
   * Answer of the flashcard
   */
  answer: S.optionalWith(S.String, { nullable: true }),
  /**
   * Difficulty level (easy, medium, hard)
   */
  difficulty_level: S.optionalWith(S.String, { nullable: true }),
  /**
   * Position for ordering within the group
   */
  position: S.optionalWith(S.Int, { nullable: true }),
}) {}

export class FlashcardRating extends S.Class<FlashcardRating>(
  'FlashcardRating',
)({
  /**
   * ID of the flashcard
   */
  flashcard_id: S.String,
  /**
   * Whether the student knew it
   */
  knew: S.Boolean,
}) {}

export class FlashcardAttemptCreate extends S.Class<FlashcardAttemptCreate>(
  'FlashcardAttemptCreate',
)({
  /**
   * One rating per card
   */
  results: S.Array(FlashcardRating).pipe(S.maxItems(100)),
}) {}

export class FlashcardResultDto extends S.Class<FlashcardResultDto>(
  'FlashcardResultDto',
)({
  /**
   * ID of the flashcard
   */
  flashcard_id: S.String,
  /**
   * Whether the student said they knew it
   */
  knew: S.Boolean,
}) {}

/**
 * A finished run through a flashcard set.
 */
export class FlashcardAttemptDto extends S.Class<FlashcardAttemptDto>(
  'FlashcardAttemptDto',
)({
  /**
   * Unique ID of the attempt
   */
  id: S.String,
  /**
   * ID of the flashcard set
   */
  group_id: S.String,
  /**
   * Run number through this set: 1 for the first
   */
  number: S.optionalWith(S.Int, { nullable: true, default: () => 1 as const }),
  /**
   * Cards the student knew
   */
  known: S.Number,
  /**
   * Cards rated
   */
  total: S.Number,
  /**
   * Result per card
   */
  results: S.Array(FlashcardResultDto),
  /**
   * When the run was finished
   */
  created_at: S.String,
}) {}

export class FlashcardAttemptStateDto extends S.Class<FlashcardAttemptStateDto>(
  'FlashcardAttemptStateDto',
)({
  /**
   * The latest run, or null if the set was not studied yet
   */
  attempt: S.optionalWith(FlashcardAttemptDto, { nullable: true }),
}) {}

/**
 * Practice record data transfer object.
 */
export class PracticeRecordDto extends S.Class<PracticeRecordDto>(
  'PracticeRecordDto',
)({
  /**
   * Unique ID of the practice record
   */
  id: S.String,
  /**
   * ID of the user
   */
  user_id: S.String,
  /**
   * ID of the project
   */
  project_id: S.String,
  /**
   * Type of study resource: flashcard or quiz
   */
  item_type: S.String,
  /**
   * ID of the study resource (flashcard or quiz question)
   */
  item_id: S.String,
  /**
   * Topic extracted from question
   */
  topic: S.String,
  /**
   * User's answer (only for quizzes, null for flashcards)
   */
  user_answer: S.optionalWith(S.String, { nullable: true }),
  /**
   * The correct answer
   */
  correct_answer: S.String,
  /**
   * Whether the user got it right
   */
  was_correct: S.Boolean,
  /**
   * FBISE SLO of the practised item, e.g. P-11-B-05
   */
  slo_code: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the practice record was created
   */
  created_at: S.String,
}) {}

export class ListPracticeRecordsApiV1ProjectsProjectIdPracticeRecordsGet200 extends S.Array(
  PracticeRecordDto,
) {}

export class PracticeRecordCreate extends S.Class<PracticeRecordCreate>(
  'PracticeRecordCreate',
)({
  /**
   * Type of study resource: flashcard or quiz
   */
  item_type: S.String.pipe(S.pattern(new RegExp('^(flashcard|quiz)$'))),
  /**
   * ID of the study resource (flashcard or quiz question)
   */
  item_id: S.String,
  /**
   * Topic extracted from question
   */
  topic: S.String.pipe(S.maxLength(500)),
  /**
   * User's answer (only for quizzes, null for flashcards)
   */
  user_answer: S.optionalWith(S.String, { nullable: true }),
  /**
   * The correct answer - flashcard answer or quiz correct option
   */
  correct_answer: S.String,
  /**
   * Whether the user got it right
   */
  was_correct: S.Boolean,
}) {}

export class PracticeRecordBatchCreate extends S.Class<PracticeRecordBatchCreate>(
  'PracticeRecordBatchCreate',
)({
  /**
   * List of practice records to create
   */
  practice_records: S.NonEmptyArray(PracticeRecordCreate).pipe(
    S.minItems(1),
    S.maxItems(100),
  ),
}) {}

export class CreatePracticeRecordsBatchApiV1ProjectsProjectIdPracticeRecordsBatchPost201 extends S.Array(
  PracticeRecordDto,
) {}

/**
 * Mind map data transfer object.
 */
export class MindMapDto extends S.Class<MindMapDto>('MindMapDto')({
  /**
   * Unique ID of the mind map
   */
  id: S.String,
  /**
   * ID of the user
   */
  user_id: S.String,
  /**
   * ID of the project
   */
  project_id: S.String,
  /**
   * Title of the mind map
   */
  title: S.String,
  /**
   * Description of the mind map
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * Structured mind map data (nodes, edges)
   */
  map_data: S.Record({ key: S.String, value: S.Unknown }),
  /**
   * Date and time the mind map was generated
   */
  generated_at: S.String,
  /**
   * Date and time the mind map was updated
   */
  updated_at: S.String,
}) {}

export class ListMindMapsApiV1ProjectsProjectIdMindMapsGet200 extends S.Array(
  MindMapDto,
) {}

export class MindMapCreate extends S.Class<MindMapCreate>('MindMapCreate')({
  /**
   * Title of the mind map
   */
  title: S.String,
  /**
   * Description of the mind map
   */
  description: S.optionalWith(S.String, { nullable: true }),
  /**
   * Custom instructions for AI generation
   */
  custom_instructions: S.optionalWith(S.String, { nullable: true }),
}) {}

export class CreateMindMapStreamApiV1ProjectsProjectIdMindMapsStreamPost200 extends S.Struct(
  {},
) {}

/**
 * Type of the resource
 */
export class StudyResourceType extends S.Literal('quiz', 'flashcard') {}

export class StudyResource extends S.Class<StudyResource>('StudyResource')({
  /**
   * ID of the resource (quiz or flashcard)
   */
  id: S.String,
  /**
   * ID of the parent (e.g. Flashcard Group ID or Quiz ID) for navigation
   */
  parent_id: S.optionalWith(S.String, { nullable: true }),
  /**
   * Type of the resource
   */
  type: StudyResourceType,
  /**
   * Title of the resource
   */
  title: S.String,
  /**
   * Optional description
   */
  description: S.optionalWith(S.String, { nullable: true }),
}) {}

export class WeeklyScheduleDay extends S.Class<WeeklyScheduleDay>(
  'WeeklyScheduleDay',
)({
  /**
   * e.g. 'Monday' or 'Day 1'
   */
  day: S.String,
  /**
   * List of tasks for the day
   */
  tasks: S.Array(S.String),
}) {}

/**
 * Schema for structured study plan content.
 */
export class StudyPlanContent extends S.Class<StudyPlanContent>(
  'StudyPlanContent',
)({
  /**
   * Brief summary of current performance and analysis.
   */
  analysis: S.String,
  /**
   * List of top 3 weak topics or areas to prioritize.
   */
  focus_areas: S.Array(S.String),
  /**
   * Specific recommended actions/resources.
   */
  action_items: S.Array(StudyResource),
  /**
   * Suggested weekly schedule.
   */
  schedule: S.Array(WeeklyScheduleDay),
  /**
   * Encouraging closing message.
   */
  encouragement: S.String,
}) {}

/**
 * Study plan data transfer object.
 */
export class StudyPlanDto extends S.Class<StudyPlanDto>('StudyPlanDto')({
  /**
   * Unique ID of the plan
   */
  id: S.String,
  /**
   * ID of the user
   */
  user_id: S.String,
  /**
   * ID of the project
   */
  project_id: S.String,
  /**
   * Structured content of the study plan
   */
  content: StudyPlanContent,
  /**
   * List of weak topics identified
   */
  weak_topics: S.optionalWith(S.Array(S.String), { nullable: true }),
  /**
   * Date created
   */
  created_at: S.String,
}) {}

export class GetLatestStudyPlanApiV1ProjectsProjectIdStudyPlansLatestGet200 extends S.Union(
  StudyPlanDto,
  S.Null,
) {}

export class ListStudyPlansApiV1ProjectsProjectIdStudyPlansGet200 extends S.Array(
  StudyPlanDto,
) {}

/**
 * DTO for usage limit information.
 */
export class UsageLimitDto extends S.Class<UsageLimitDto>('UsageLimitDto')({
  /**
   * Number of operations used today
   */
  used: S.Int,
  /**
   * Maximum number of operations allowed per day
   */
  limit: S.Int,
}) {}

/**
 * DTO for user usage statistics.
 */
export class UsageDto extends S.Class<UsageDto>('UsageDto')({
  /**
   * Chat message usage statistics
   */
  chat_messages: UsageLimitDto,
  /**
   * Flashcard generation usage statistics
   */
  flashcard_generations: UsageLimitDto,
  /**
   * Quiz generation usage statistics
   */
  quiz_generations: UsageLimitDto,
  /**
   * Mind map generation usage statistics
   */
  mindmap_generations: UsageLimitDto,
  /**
   * Document upload usage statistics
   */
  document_uploads: UsageLimitDto,
}) {}

export class UserDto extends S.Class<UserDto>('UserDto')({
  /**
   * Unique ID of the user
   */
  id: S.String,
  /**
   * Name of the user
   */
  name: S.optionalWith(S.String, { nullable: true }),
  /**
   * Email of the user
   */
  email: S.optionalWith(S.String, { nullable: true }),
  /**
   * Date and time the user was created
   */
  created_at: S.String,
  /**
   * Date and time the user was updated
   */
  updated_at: S.String,
}) {}

export class ListUsersApiV1UsersGet200 extends S.Array(UserDto) {}

export const make = (
  httpClient: HttpClient.HttpClient,
  options: {
    readonly transformClient?:
      | ((
          client: HttpClient.HttpClient,
        ) => Effect.Effect<HttpClient.HttpClient>)
      | undefined
  } = {},
): Client => {
  const unexpectedStatus = (response: HttpClientResponse.HttpClientResponse) =>
    Effect.flatMap(
      Effect.orElseSucceed(response.json, () => 'Unexpected status code'),
      (description) =>
        Effect.fail(
          new HttpClientError.ResponseError({
            request: response.request,
            response,
            reason: 'StatusCode',
            description:
              typeof description === 'string'
                ? description
                : JSON.stringify(description),
          }),
        ),
    )
  const withResponse: <A, E>(
    f: (response: HttpClientResponse.HttpClientResponse) => Effect.Effect<A, E>,
  ) => (
    request: HttpClientRequest.HttpClientRequest,
  ) => Effect.Effect<any, any> = options.transformClient
    ? (f) => (request) =>
        Effect.flatMap(
          Effect.flatMap(options.transformClient!(httpClient), (client) =>
            client.execute(request),
          ),
          f,
        )
    : (f) => (request) => Effect.flatMap(httpClient.execute(request), f)
  const decodeSuccess =
    <A, I, R>(schema: S.Schema<A, I, R>) =>
    (response: HttpClientResponse.HttpClientResponse) =>
      HttpClientResponse.schemaBodyJson(schema)(response)
  const decodeError =
    <const Tag extends string, A, I, R>(tag: Tag, schema: S.Schema<A, I, R>) =>
    (response: HttpClientResponse.HttpClientResponse) =>
      Effect.flatMap(
        HttpClientResponse.schemaBodyJson(schema)(response),
        (cause) => Effect.fail(ClientError(tag, cause, response)),
      )
  return {
    httpClient,
    healthCheckHealthGet: () =>
      HttpClientRequest.get(`/health`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(HealthCheckHealthGet200),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getProfileApiV1ProfileGet: () =>
      HttpClientRequest.get(`/api/v1/profile`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ProfileStateDto),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    updateProfileApiV1ProfilePut: (options) =>
      HttpClientRequest.put(`/api/v1/profile`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(StudentProfileDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    completeOnboardingApiV1OnboardingPost: (options) =>
      HttpClientRequest.post(`/api/v1/onboarding`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(OnboardingResultDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getProgressApiV1ProgressGet: () =>
      HttpClientRequest.get(`/api/v1/progress`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ProgressDto),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listGradeSubjectsApiV1CurriculumGradeSubjectsGet: (options) =>
      HttpClientRequest.get(`/api/v1/curriculum/grade-subjects`).pipe(
        HttpClientRequest.setUrlParams({ grade: options?.['grade'] as any }),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListGradeSubjectsApiV1CurriculumGradeSubjectsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getCurriculumTreeApiV1CurriculumGradeSubjectsGradeSubjectIdTreeGet: (
      gradeSubjectId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/curriculum/grade-subjects/${gradeSubjectId}/tree`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(CurriculumTreeDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getSloApiV1CurriculumSlosCodeGet: (code, options) =>
      HttpClientRequest.get(`/api/v1/curriculum/slos/${code}`).pipe(
        HttpClientRequest.setUrlParams({
          grade_subject_id: options?.['grade_subject_id'] as any,
        }),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(SloDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getSloExplainerApiV1CurriculumGradeSubjectsGradeSubjectIdSlosCodeExplainerGet:
      (gradeSubjectId, code) =>
        HttpClientRequest.get(
          `/api/v1/curriculum/grade-subjects/${gradeSubjectId}/slos/${code}/explainer`,
        ).pipe(
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(SloExplainerStateDto),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    listProjectsApiV1ProjectsGet: () =>
      HttpClientRequest.get(`/api/v1/projects`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ListProjectsApiV1ProjectsGet200),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createProjectApiV1ProjectsPost: (options) =>
      HttpClientRequest.post(`/api/v1/projects`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ProjectDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getProjectApiV1ProjectsProjectIdGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ProjectDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteProjectApiV1ProjectsProjectIdDelete: (projectId) =>
      HttpClientRequest.del(`/api/v1/projects/${projectId}`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    updateProjectApiV1ProjectsProjectIdPatch: (projectId, options) =>
      HttpClientRequest.patch(`/api/v1/projects/${projectId}`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ProjectDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    uploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost: (
      projectId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/documents/upload`,
      ).pipe(
        HttpClientRequest.bodyFormDataRecord(options as any),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              UploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost201,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listDocumentsApiV1ProjectsProjectIdDocumentsGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/documents`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListDocumentsApiV1ProjectsProjectIdDocumentsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createDocumentApiV1ProjectsProjectIdDocumentsPost: (projectId, options) =>
      HttpClientRequest.post(`/api/v1/projects/${projectId}/documents`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(DocumentDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getDocumentApiV1ProjectsProjectIdDocumentsDocumentIdGet: (
      projectId,
      documentId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/documents/${documentId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(DocumentDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteDocumentApiV1ProjectsProjectIdDocumentsDocumentIdDelete: (
      projectId,
      documentId,
    ) =>
      HttpClientRequest.del(
        `/api/v1/projects/${projectId}/documents/${documentId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    updateDocumentApiV1ProjectsProjectIdDocumentsDocumentIdPatch: (
      projectId,
      documentId,
      options,
    ) =>
      HttpClientRequest.patch(
        `/api/v1/projects/${projectId}/documents/${documentId}`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(DocumentDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getDocumentPreviewApiV1ProjectsProjectIdDocumentsDocumentIdPreviewGet: (
      projectId,
      documentId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/documents/${documentId}/preview`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(DocumentPreviewDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listChatsApiV1ProjectsProjectIdChatsGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/chats`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ListChatsApiV1ProjectsProjectIdChatsGet200),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createChatApiV1ProjectsProjectIdChatsPost: (projectId, options) =>
      HttpClientRequest.post(`/api/v1/projects/${projectId}/chats`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ChatDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getChatApiV1ProjectsProjectIdChatsChatIdGet: (projectId, chatId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/chats/${chatId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ChatDetailDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteChatApiV1ProjectsProjectIdChatsChatIdDelete: (projectId, chatId) =>
      HttpClientRequest.del(
        `/api/v1/projects/${projectId}/chats/${chatId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    updateChatApiV1ProjectsProjectIdChatsChatIdPatch: (
      projectId,
      chatId,
      options,
    ) =>
      HttpClientRequest.patch(
        `/api/v1/projects/${projectId}/chats/${chatId}`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ChatDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    sendStreamingMessageApiV1ProjectsProjectIdChatsChatIdMessagesStreamPost: (
      projectId,
      chatId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/chats/${chatId}/messages/stream`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              SendStreamingMessageApiV1ProjectsProjectIdChatsChatIdMessagesStreamPost200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listNotesApiV1ProjectsProjectIdNotesGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/notes`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ListNotesApiV1ProjectsProjectIdNotesGet200),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createNoteApiV1ProjectsProjectIdNotesPost: (projectId, options) =>
      HttpClientRequest.post(`/api/v1/projects/${projectId}/notes`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(NoteDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getNoteApiV1ProjectsProjectIdNotesNoteIdGet: (projectId, noteId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/notes/${noteId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(NoteDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteNoteApiV1ProjectsProjectIdNotesNoteIdDelete: (projectId, noteId) =>
      HttpClientRequest.del(
        `/api/v1/projects/${projectId}/notes/${noteId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    updateNoteApiV1ProjectsProjectIdNotesNoteIdPatch: (
      projectId,
      noteId,
      options,
    ) =>
      HttpClientRequest.patch(
        `/api/v1/projects/${projectId}/notes/${noteId}`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(NoteDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    generateNoteApiV1ProjectsProjectIdNotesNoteIdGeneratePost: (
      projectId,
      noteId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/notes/${noteId}/generate`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(NoteDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    generateNoteStreamApiV1ProjectsProjectIdNotesNoteIdGenerateStreamPost: (
      projectId,
      noteId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/notes/${noteId}/generate/stream`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              GenerateNoteStreamApiV1ProjectsProjectIdNotesNoteIdGenerateStreamPost200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listQuizzesApiV1ProjectsProjectIdQuizzesGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/quizzes`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListQuizzesApiV1ProjectsProjectIdQuizzesGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createQuizApiV1ProjectsProjectIdQuizzesPost: (projectId, options) =>
      HttpClientRequest.post(`/api/v1/projects/${projectId}/quizzes`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getQuizApiV1ProjectsProjectIdQuizzesQuizIdGet: (projectId, quizId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/quizzes/${quizId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteQuizApiV1ProjectsProjectIdQuizzesQuizIdDelete: (projectId, quizId) =>
      HttpClientRequest.del(
        `/api/v1/projects/${projectId}/quizzes/${quizId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    updateQuizApiV1ProjectsProjectIdQuizzesQuizIdPatch: (
      projectId,
      quizId,
      options,
    ) =>
      HttpClientRequest.patch(
        `/api/v1/projects/${projectId}/quizzes/${quizId}`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    generateQuizApiV1ProjectsProjectIdQuizzesQuizIdGeneratePost: (
      projectId,
      quizId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/quizzes/${quizId}/generate`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    generateQuizStreamApiV1ProjectsProjectIdQuizzesQuizIdGenerateStreamPost: (
      projectId,
      quizId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/quizzes/${quizId}/generate/stream`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              GenerateQuizStreamApiV1ProjectsProjectIdQuizzesQuizIdGenerateStreamPost200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsGet: (
      projectId,
      quizId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/quizzes/${quizId}/questions`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsPost: (
      projectId,
      quizId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/quizzes/${quizId}/questions`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizQuestionDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsQuestionIdGet: (
      projectId,
      quizId,
      questionId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/quizzes/${quizId}/questions/${questionId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizQuestionDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsQuestionIdDelete:
      (projectId, quizId, questionId) =>
        HttpClientRequest.del(
          `/api/v1/projects/${projectId}/quizzes/${quizId}/questions/${questionId}`,
        ).pipe(
          withResponse(
            HttpClientResponse.matchStatus({
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              '204': () => Effect.void,
              orElse: unexpectedStatus,
            }),
          ),
        ),
    updateQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsQuestionIdPatch:
      (projectId, quizId, questionId, options) =>
        HttpClientRequest.patch(
          `/api/v1/projects/${projectId}/quizzes/${quizId}/questions/${questionId}`,
        ).pipe(
          HttpClientRequest.bodyUnsafeJson(options),
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(QuizQuestionDto),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    reorderQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsReorderPatch:
      (projectId, quizId, options) =>
        HttpClientRequest.patch(
          `/api/v1/projects/${projectId}/quizzes/${quizId}/questions/reorder`,
        ).pipe(
          HttpClientRequest.bodyUnsafeJson(options),
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(
                ReorderQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsReorderPatch200,
              ),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    submitQuizAttemptApiV1ProjectsProjectIdQuizzesQuizIdAttemptsPost: (
      projectId,
      quizId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/quizzes/${quizId}/attempts`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizAttemptDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getLatestQuizAttemptApiV1ProjectsProjectIdQuizzesQuizIdAttemptsLatestGet: (
      projectId,
      quizId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/quizzes/${quizId}/attempts/latest`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(QuizAttemptStateDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listSrqsApiV1ProjectsProjectIdSrqGet: (projectId, options) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/srq`).pipe(
        HttpClientRequest.setUrlParams({
          slo_code: options?.['slo_code'] as any,
        }),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ListSrqsApiV1ProjectsProjectIdSrqGet200),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createSrqApiV1ProjectsProjectIdSrqPost: (projectId, options) =>
      HttpClientRequest.post(`/api/v1/projects/${projectId}/srq`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(SrqQuestionDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getSrqApiV1ProjectsProjectIdSrqQuestionIdGet: (projectId, questionId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/srq/${questionId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(SrqDetailDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    markSrqApiV1ProjectsProjectIdSrqQuestionIdMarkPost: (
      projectId,
      questionId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/srq/${questionId}/mark`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(SrqAttemptDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listPapersApiV1ProjectsProjectIdPapersGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/papers`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ListPapersApiV1ProjectsProjectIdPapersGet200),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createPaperApiV1ProjectsProjectIdPapersPost: (projectId, options) =>
      HttpClientRequest.post(`/api/v1/projects/${projectId}/papers`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(PaperDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getPaperApiV1ProjectsProjectIdPapersPaperIdGet: (projectId, paperId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/papers/${paperId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(PaperDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    savePaperAnswersApiV1ProjectsProjectIdPapersPaperIdAnswersPut: (
      projectId,
      paperId,
      options,
    ) =>
      HttpClientRequest.put(
        `/api/v1/projects/${projectId}/papers/${paperId}/answers`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    submitPaperApiV1ProjectsProjectIdPapersPaperIdSubmitPost: (
      projectId,
      paperId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/papers/${paperId}/submit`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(PaperDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listPracticeHistoryApiV1ProjectsProjectIdAttemptsGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/attempts`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListPracticeHistoryApiV1ProjectsProjectIdAttemptsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getReviewerStateApiV1ReviewMeGet: () =>
      HttpClientRequest.get(`/api/v1/review/me`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ReviewerStateDto),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listReviewItemsApiV1ReviewItemsGet: (options) =>
      HttpClientRequest.get(`/api/v1/review/items`).pipe(
        HttpClientRequest.setUrlParams({
          grade_subject_id: options?.['grade_subject_id'] as any,
          domain_code: options?.['domain_code'] as any,
          kind: options?.['kind'] as any,
          review_status: options?.['review_status'] as any,
          slo_code: options?.['slo_code'] as any,
        }),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ListReviewItemsApiV1ReviewItemsGet200),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    reviewSummaryApiV1ReviewSummaryGet: (options) =>
      HttpClientRequest.get(`/api/v1/review/summary`).pipe(
        HttpClientRequest.setUrlParams({
          grade_subject_id: options?.['grade_subject_id'] as any,
        }),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ReviewSummaryApiV1ReviewSummaryGet200),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    reviewItemApiV1ReviewItemsItemIdPatch: (itemId, options) =>
      HttpClientRequest.patch(`/api/v1/review/items/${itemId}`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ContentItemDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listFlashcardGroupsApiV1ProjectsProjectIdFlashcardGroupsGet: (projectId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/flashcard-groups`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListFlashcardGroupsApiV1ProjectsProjectIdFlashcardGroupsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsPost: (
      projectId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/flashcard-groups`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(FlashcardGroupDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsGroupIdGet: (
      projectId,
      groupId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/flashcard-groups/${groupId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(FlashcardGroupDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsGroupIdDelete: (
      projectId,
      groupId,
    ) =>
      HttpClientRequest.del(
        `/api/v1/projects/${projectId}/flashcard-groups/${groupId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    updateFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsGroupIdPatch: (
      projectId,
      groupId,
      options,
    ) =>
      HttpClientRequest.patch(
        `/api/v1/projects/${projectId}/flashcard-groups/${groupId}`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(FlashcardGroupDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    generateFlashcardsApiV1ProjectsProjectIdFlashcardGroupsGroupIdGeneratePost:
      (projectId, groupId, options) =>
        HttpClientRequest.post(
          `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/generate`,
        ).pipe(
          HttpClientRequest.bodyUnsafeJson(options),
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(FlashcardGroupDto),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    generateFlashcardsStreamApiV1ProjectsProjectIdFlashcardGroupsGroupIdGenerateStreamPost:
      (projectId, groupId, options) =>
        HttpClientRequest.post(
          `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/generate/stream`,
        ).pipe(
          HttpClientRequest.bodyUnsafeJson(options),
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(
                GenerateFlashcardsStreamApiV1ProjectsProjectIdFlashcardGroupsGroupIdGenerateStreamPost200,
              ),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    listFlashcardsApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsGet: (
      projectId,
      groupId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/flashcards`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListFlashcardsApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsPost: (
      projectId,
      groupId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/flashcards`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(FlashcardDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsFlashcardIdGet:
      (projectId, groupId, flashcardId) =>
        HttpClientRequest.get(
          `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/flashcards/${flashcardId}`,
        ).pipe(
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(FlashcardDto),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    deleteFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsFlashcardIdDelete:
      (projectId, groupId, flashcardId) =>
        HttpClientRequest.del(
          `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/flashcards/${flashcardId}`,
        ).pipe(
          withResponse(
            HttpClientResponse.matchStatus({
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              '204': () => Effect.void,
              orElse: unexpectedStatus,
            }),
          ),
        ),
    updateFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsFlashcardIdPatch:
      (projectId, groupId, flashcardId, options) =>
        HttpClientRequest.patch(
          `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/flashcards/${flashcardId}`,
        ).pipe(
          HttpClientRequest.bodyUnsafeJson(options),
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(FlashcardDto),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    submitFlashcardAttemptApiV1ProjectsProjectIdFlashcardGroupsGroupIdAttemptsPost:
      (projectId, groupId, options) =>
        HttpClientRequest.post(
          `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/attempts`,
        ).pipe(
          HttpClientRequest.bodyUnsafeJson(options),
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(FlashcardAttemptDto),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    getLatestFlashcardAttemptApiV1ProjectsProjectIdFlashcardGroupsGroupIdAttemptsLatestGet:
      (projectId, groupId) =>
        HttpClientRequest.get(
          `/api/v1/projects/${projectId}/flashcard-groups/${groupId}/attempts/latest`,
        ).pipe(
          withResponse(
            HttpClientResponse.matchStatus({
              '2xx': decodeSuccess(FlashcardAttemptStateDto),
              '422': decodeError('HTTPValidationError', HTTPValidationError),
              orElse: unexpectedStatus,
            }),
          ),
        ),
    listPracticeRecordsApiV1ProjectsProjectIdPracticeRecordsGet: (projectId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/practice-records`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListPracticeRecordsApiV1ProjectsProjectIdPracticeRecordsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createPracticeRecordApiV1ProjectsProjectIdPracticeRecordsPost: (
      projectId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/practice-records`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(PracticeRecordDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createPracticeRecordsBatchApiV1ProjectsProjectIdPracticeRecordsBatchPost: (
      projectId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/practice-records/batch`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              CreatePracticeRecordsBatchApiV1ProjectsProjectIdPracticeRecordsBatchPost201,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listMindMapsApiV1ProjectsProjectIdMindMapsGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/mind-maps`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListMindMapsApiV1ProjectsProjectIdMindMapsGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createMindMapApiV1ProjectsProjectIdMindMapsPost: (projectId, options) =>
      HttpClientRequest.post(`/api/v1/projects/${projectId}/mind-maps`).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(MindMapDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getMindMapApiV1ProjectsProjectIdMindMapsMindMapIdGet: (
      projectId,
      mindMapId,
    ) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/mind-maps/${mindMapId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(MindMapDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteMindMapApiV1ProjectsProjectIdMindMapsMindMapIdDelete: (
      projectId,
      mindMapId,
    ) =>
      HttpClientRequest.del(
        `/api/v1/projects/${projectId}/mind-maps/${mindMapId}`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    createMindMapStreamApiV1ProjectsProjectIdMindMapsStreamPost: (
      projectId,
      options,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/mind-maps/stream`,
      ).pipe(
        HttpClientRequest.bodyUnsafeJson(options),
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              CreateMindMapStreamApiV1ProjectsProjectIdMindMapsStreamPost200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getLatestStudyPlanApiV1ProjectsProjectIdStudyPlansLatestGet: (projectId) =>
      HttpClientRequest.get(
        `/api/v1/projects/${projectId}/study-plans/latest`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              GetLatestStudyPlanApiV1ProjectsProjectIdStudyPlansLatestGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listStudyPlansApiV1ProjectsProjectIdStudyPlansGet: (projectId) =>
      HttpClientRequest.get(`/api/v1/projects/${projectId}/study-plans`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(
              ListStudyPlansApiV1ProjectsProjectIdStudyPlansGet200,
            ),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    generateStudyPlanApiV1ProjectsProjectIdStudyPlansGeneratePost: (
      projectId,
    ) =>
      HttpClientRequest.post(
        `/api/v1/projects/${projectId}/study-plans/generate`,
      ).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(StudyPlanDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getUsageApiV1UsageGet: () =>
      HttpClientRequest.get(`/api/v1/usage`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(UsageDto),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getUserApiV1UsersUserIdGet: (userId) =>
      HttpClientRequest.get(`/api/v1/users/${userId}`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(UserDto),
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    deleteUserApiV1UsersUserIdDelete: (userId) =>
      HttpClientRequest.del(`/api/v1/users/${userId}`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '422': decodeError('HTTPValidationError', HTTPValidationError),
            '204': () => Effect.void,
            orElse: unexpectedStatus,
          }),
        ),
      ),
    listUsersApiV1UsersGet: () =>
      HttpClientRequest.get(`/api/v1/users`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(ListUsersApiV1UsersGet200),
            orElse: unexpectedStatus,
          }),
        ),
      ),
    getCurrentUserInfoApiV1AuthMeGet: () =>
      HttpClientRequest.get(`/api/v1/auth/me`).pipe(
        withResponse(
          HttpClientResponse.matchStatus({
            '2xx': decodeSuccess(UserDto),
            orElse: unexpectedStatus,
          }),
        ),
      ),
  }
}

export interface Client {
  readonly httpClient: HttpClient.HttpClient
  /**
   * Health Check
   */
  readonly healthCheckHealthGet: () => Effect.Effect<
    typeof HealthCheckHealthGet200.Type,
    HttpClientError.HttpClientError | ParseError
  >
  /**
   * Get the student's profile and whether onboarding is complete.
   */
  readonly getProfileApiV1ProfileGet: () => Effect.Effect<
    typeof ProfileStateDto.Type,
    HttpClientError.HttpClientError | ParseError
  >
  /**
   * Update the explanation language or exam year.
   */
  readonly updateProfileApiV1ProfilePut: (
    options: typeof ProfileUpdate.Encoded,
  ) => Effect.Effect<
    typeof StudentProfileDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Save grade, group and language, and create the subject workspaces.
   */
  readonly completeOnboardingApiV1OnboardingPost: (
    options: typeof OnboardingRequest.Encoded,
  ) => Effect.Effect<
    typeof OnboardingResultDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Mastery per subject and domain, weakest SLOs and a predicted grade band.
   */
  readonly getProgressApiV1ProgressGet: () => Effect.Effect<
    typeof ProgressDto.Type,
    HttpClientError.HttpClientError | ParseError
  >
  /**
   * List FSc subjects per grade and whether their SLOs are available.
   */
  readonly listGradeSubjectsApiV1CurriculumGradeSubjectsGet: (
    options?:
      | typeof ListGradeSubjectsApiV1CurriculumGradeSubjectsGetParams.Encoded
      | undefined,
  ) => Effect.Effect<
    typeof ListGradeSubjectsApiV1CurriculumGradeSubjectsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get the syllabus map: domains and SLOs with the student's mastery.
   */
  readonly getCurriculumTreeApiV1CurriculumGradeSubjectsGradeSubjectIdTreeGet: (
    gradeSubjectId: string,
  ) => Effect.Effect<
    typeof CurriculumTreeDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get one SLO by its FBISE code, e.g. P-11-B-05.
   */
  readonly getSloApiV1CurriculumSlosCodeGet: (
    code: string,
    options?: typeof GetSloApiV1CurriculumSlosCodeGetParams.Encoded | undefined,
  ) => Effect.Effect<
    typeof SloDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * The prepared explainer for an SLO, if one has been written.
   */
  readonly getSloExplainerApiV1CurriculumGradeSubjectsGradeSubjectIdSlosCodeExplainerGet: (
    gradeSubjectId: string,
    code: string,
  ) => Effect.Effect<
    typeof SloExplainerStateDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all projects for a user.
   */
  readonly listProjectsApiV1ProjectsGet: () => Effect.Effect<
    typeof ListProjectsApiV1ProjectsGet200.Type,
    HttpClientError.HttpClientError | ParseError
  >
  /**
   * Create a new project.
   */
  readonly createProjectApiV1ProjectsPost: (
    options: typeof ProjectCreate.Encoded,
  ) => Effect.Effect<
    typeof ProjectDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a project by ID.
   */
  readonly getProjectApiV1ProjectsProjectIdGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ProjectDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a project.
   */
  readonly deleteProjectApiV1ProjectsProjectIdDelete: (
    projectId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a project.
   */
  readonly updateProjectApiV1ProjectsProjectIdPatch: (
    projectId: string,
    options: typeof ProjectUpdate.Encoded,
  ) => Effect.Effect<
    typeof ProjectDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Upload one or more documents. Processing happens asynchronously in background.
   */
  readonly uploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost: (
    projectId: string,
    options: typeof BodyUploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost.Encoded,
  ) => Effect.Effect<
    typeof UploadDocumentApiV1ProjectsProjectIdDocumentsUploadPost201.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all documents for a project.
   */
  readonly listDocumentsApiV1ProjectsProjectIdDocumentsGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListDocumentsApiV1ProjectsProjectIdDocumentsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a new document.
   */
  readonly createDocumentApiV1ProjectsProjectIdDocumentsPost: (
    projectId: string,
    options: typeof DocumentCreate.Encoded,
  ) => Effect.Effect<
    typeof DocumentDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a document by ID.
   */
  readonly getDocumentApiV1ProjectsProjectIdDocumentsDocumentIdGet: (
    projectId: string,
    documentId: string,
  ) => Effect.Effect<
    typeof DocumentDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a document.
   */
  readonly deleteDocumentApiV1ProjectsProjectIdDocumentsDocumentIdDelete: (
    projectId: string,
    documentId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a document.
   */
  readonly updateDocumentApiV1ProjectsProjectIdDocumentsDocumentIdPatch: (
    projectId: string,
    documentId: string,
    options: typeof DocumentUpdate.Encoded,
  ) => Effect.Effect<
    typeof DocumentDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a preview URL for a document.
   */
  readonly getDocumentPreviewApiV1ProjectsProjectIdDocumentsDocumentIdPreviewGet: (
    projectId: string,
    documentId: string,
  ) => Effect.Effect<
    typeof DocumentPreviewDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all chats for a project.
   */
  readonly listChatsApiV1ProjectsProjectIdChatsGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListChatsApiV1ProjectsProjectIdChatsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a new chat.
   */
  readonly createChatApiV1ProjectsProjectIdChatsPost: (
    projectId: string,
    options: typeof ChatCreate.Encoded,
  ) => Effect.Effect<
    typeof ChatDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a chat by ID with messages and parts.
   */
  readonly getChatApiV1ProjectsProjectIdChatsChatIdGet: (
    projectId: string,
    chatId: string,
  ) => Effect.Effect<
    typeof ChatDetailDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a chat.
   */
  readonly deleteChatApiV1ProjectsProjectIdChatsChatIdDelete: (
    projectId: string,
    chatId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a chat.
   */
  readonly updateChatApiV1ProjectsProjectIdChatsChatIdPatch: (
    projectId: string,
    chatId: string,
    options: typeof ChatUpdate.Encoded,
  ) => Effect.Effect<
    typeof ChatDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Send a message to a chat with streaming response
   */
  readonly sendStreamingMessageApiV1ProjectsProjectIdChatsChatIdMessagesStreamPost: (
    projectId: string,
    chatId: string,
    options: typeof ChatCompletionRequest.Encoded,
  ) => Effect.Effect<
    typeof SendStreamingMessageApiV1ProjectsProjectIdChatsChatIdMessagesStreamPost200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all notes for a project.
   */
  readonly listNotesApiV1ProjectsProjectIdNotesGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListNotesApiV1ProjectsProjectIdNotesGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a new note.
   */
  readonly createNoteApiV1ProjectsProjectIdNotesPost: (
    projectId: string,
    options: typeof NoteCreate.Encoded,
  ) => Effect.Effect<
    typeof NoteDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a note by ID.
   */
  readonly getNoteApiV1ProjectsProjectIdNotesNoteIdGet: (
    projectId: string,
    noteId: string,
  ) => Effect.Effect<
    typeof NoteDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a note.
   */
  readonly deleteNoteApiV1ProjectsProjectIdNotesNoteIdDelete: (
    projectId: string,
    noteId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a note.
   */
  readonly updateNoteApiV1ProjectsProjectIdNotesNoteIdPatch: (
    projectId: string,
    noteId: string,
    options: typeof NoteUpdate.Encoded,
  ) => Effect.Effect<
    typeof NoteDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Queue note generation request to be processed by a worker.
   */
  readonly generateNoteApiV1ProjectsProjectIdNotesNoteIdGeneratePost: (
    projectId: string,
    noteId: string,
    options: typeof GenerateRequest.Encoded,
  ) => Effect.Effect<
    typeof NoteDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Queue note generation request with streaming progress updates.
   */
  readonly generateNoteStreamApiV1ProjectsProjectIdNotesNoteIdGenerateStreamPost: (
    projectId: string,
    noteId: string,
    options: typeof GenerateRequest.Encoded,
  ) => Effect.Effect<
    typeof GenerateNoteStreamApiV1ProjectsProjectIdNotesNoteIdGenerateStreamPost200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all quizzes for a project.
   */
  readonly listQuizzesApiV1ProjectsProjectIdQuizzesGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListQuizzesApiV1ProjectsProjectIdQuizzesGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a new quiz.
   */
  readonly createQuizApiV1ProjectsProjectIdQuizzesPost: (
    projectId: string,
    options: typeof QuizCreate.Encoded,
  ) => Effect.Effect<
    typeof QuizDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a quiz by ID.
   */
  readonly getQuizApiV1ProjectsProjectIdQuizzesQuizIdGet: (
    projectId: string,
    quizId: string,
  ) => Effect.Effect<
    typeof QuizDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a quiz.
   */
  readonly deleteQuizApiV1ProjectsProjectIdQuizzesQuizIdDelete: (
    projectId: string,
    quizId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a quiz.
   */
  readonly updateQuizApiV1ProjectsProjectIdQuizzesQuizIdPatch: (
    projectId: string,
    quizId: string,
    options: typeof QuizUpdate.Encoded,
  ) => Effect.Effect<
    typeof QuizDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Queue quiz generation request to be processed by a worker.
   */
  readonly generateQuizApiV1ProjectsProjectIdQuizzesQuizIdGeneratePost: (
    projectId: string,
    quizId: string,
    options: typeof GenerateRequest.Encoded,
  ) => Effect.Effect<
    typeof QuizDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Queue quiz generation request with streaming progress updates.
   */
  readonly generateQuizStreamApiV1ProjectsProjectIdQuizzesQuizIdGenerateStreamPost: (
    projectId: string,
    quizId: string,
    options: typeof GenerateRequest.Encoded,
  ) => Effect.Effect<
    typeof GenerateQuizStreamApiV1ProjectsProjectIdQuizzesQuizIdGenerateStreamPost200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all questions in a quiz.
   */
  readonly listQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsGet: (
    projectId: string,
    quizId: string,
  ) => Effect.Effect<
    typeof ListQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a new question in a quiz.
   */
  readonly createQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsPost: (
    projectId: string,
    quizId: string,
    options: typeof QuizQuestionCreate.Encoded,
  ) => Effect.Effect<
    typeof QuizQuestionDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a question by ID.
   */
  readonly getQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsQuestionIdGet: (
    projectId: string,
    quizId: string,
    questionId: string,
  ) => Effect.Effect<
    typeof QuizQuestionDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a question.
   */
  readonly deleteQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsQuestionIdDelete: (
    projectId: string,
    quizId: string,
    questionId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a question.
   */
  readonly updateQuizQuestionApiV1ProjectsProjectIdQuizzesQuizIdQuestionsQuestionIdPatch: (
    projectId: string,
    quizId: string,
    questionId: string,
    options: typeof QuizQuestionUpdate.Encoded,
  ) => Effect.Effect<
    typeof QuizQuestionDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Reorder questions in a quiz.
   */
  readonly reorderQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsReorderPatch: (
    projectId: string,
    quizId: string,
    options: typeof QuizQuestionReorder.Encoded,
  ) => Effect.Effect<
    typeof ReorderQuizQuestionsApiV1ProjectsProjectIdQuizzesQuizIdQuestionsReorderPatch200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Score a finished quiz on the server and record the answers for SLO mastery.
   */
  readonly submitQuizAttemptApiV1ProjectsProjectIdQuizzesQuizIdAttemptsPost: (
    projectId: string,
    quizId: string,
    options: typeof QuizAttemptCreate.Encoded,
  ) => Effect.Effect<
    typeof QuizAttemptDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * The student's most recent attempt at this quiz (if any) and all their attempts.
   */
  readonly getLatestQuizAttemptApiV1ProjectsProjectIdQuizzesQuizIdAttemptsLatestGet: (
    projectId: string,
    quizId: string,
  ) => Effect.Effect<
    typeof QuizAttemptStateDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List the project's short-response questions, newest first.
   */
  readonly listSrqsApiV1ProjectsProjectIdSrqGet: (
    projectId: string,
    options?:
      | typeof ListSrqsApiV1ProjectsProjectIdSrqGetParams.Encoded
      | undefined,
  ) => Effect.Effect<
    typeof ListSrqsApiV1ProjectsProjectIdSrqGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Generate a short-response question for an SLO (takes a few seconds).
   */
  readonly createSrqApiV1ProjectsProjectIdSrqPost: (
    projectId: string,
    options: typeof SrqCreate.Encoded,
  ) => Effect.Effect<
    typeof SrqQuestionDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a question with the student's marked answers.
   */
  readonly getSrqApiV1ProjectsProjectIdSrqQuestionIdGet: (
    projectId: string,
    questionId: string,
  ) => Effect.Effect<
    typeof SrqDetailDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Mark a written answer like an FBISE examiner (AI-estimated marks).
   */
  readonly markSrqApiV1ProjectsProjectIdSrqQuestionIdMarkPost: (
    projectId: string,
    questionId: string,
    options: typeof SrqAnswer.Encoded,
  ) => Effect.Effect<
    typeof SrqAttemptDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * The student's practice papers in this workspace, newest first.
   */
  readonly listPapersApiV1ProjectsProjectIdPapersGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListPapersApiV1ProjectsProjectIdPapersGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Assemble a practice paper (takes a few seconds).
   */
  readonly createPaperApiV1ProjectsProjectIdPapersPost: (
    projectId: string,
    options: typeof PaperCreate.Encoded,
  ) => Effect.Effect<
    typeof PaperDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * A paper; marks and model answers are included once it is submitted.
   */
  readonly getPaperApiV1ProjectsProjectIdPapersPaperIdGet: (
    projectId: string,
    paperId: string,
  ) => Effect.Effect<
    typeof PaperDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Save answers while the student works.
   */
  readonly savePaperAnswersApiV1ProjectsProjectIdPapersPaperIdAnswersPut: (
    projectId: string,
    paperId: string,
    options: typeof PaperAnswers.Encoded,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Submit and mark the paper (written answers are AI-estimated, like an examiner).
   */
  readonly submitPaperApiV1ProjectsProjectIdPapersPaperIdSubmitPost: (
    projectId: string,
    paperId: string,
    options: typeof PaperAnswers.Encoded,
  ) => Effect.Effect<
    typeof PaperDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Every finished quiz, flashcard run and paper in this workspace, newest first.
   */
  readonly listPracticeHistoryApiV1ProjectsProjectIdAttemptsGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListPracticeHistoryApiV1ProjectsProjectIdAttemptsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Whether the current user may review content.
   */
  readonly getReviewerStateApiV1ReviewMeGet: () => Effect.Effect<
    typeof ReviewerStateDto.Type,
    HttpClientError.HttpClientError | ParseError
  >
  /**
   * Content items in syllabus order.
   */
  readonly listReviewItemsApiV1ReviewItemsGet: (
    options: typeof ListReviewItemsApiV1ReviewItemsGetParams.Encoded,
  ) => Effect.Effect<
    typeof ListReviewItemsApiV1ReviewItemsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Item counts per kind and review status.
   */
  readonly reviewSummaryApiV1ReviewSummaryGet: (
    options: typeof ReviewSummaryApiV1ReviewSummaryGetParams.Encoded,
  ) => Effect.Effect<
    typeof ReviewSummaryApiV1ReviewSummaryGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Approve or reject an item, with an optional note on what to fix.
   */
  readonly reviewItemApiV1ReviewItemsItemIdPatch: (
    itemId: string,
    options: typeof ContentReview.Encoded,
  ) => Effect.Effect<
    typeof ContentItemDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all flashcard groups for a project.
   */
  readonly listFlashcardGroupsApiV1ProjectsProjectIdFlashcardGroupsGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListFlashcardGroupsApiV1ProjectsProjectIdFlashcardGroupsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a new flashcard group.
   */
  readonly createFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsPost: (
    projectId: string,
    options: typeof FlashcardGroupCreate.Encoded,
  ) => Effect.Effect<
    typeof FlashcardGroupDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a flashcard group by ID.
   */
  readonly getFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsGroupIdGet: (
    projectId: string,
    groupId: string,
  ) => Effect.Effect<
    typeof FlashcardGroupDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a flashcard group.
   */
  readonly deleteFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsGroupIdDelete: (
    projectId: string,
    groupId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a flashcard group.
   */
  readonly updateFlashcardGroupApiV1ProjectsProjectIdFlashcardGroupsGroupIdPatch: (
    projectId: string,
    groupId: string,
    options: typeof FlashcardGroupUpdate.Encoded,
  ) => Effect.Effect<
    typeof FlashcardGroupDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Queue flashcard generation request to be processed by a worker.
   */
  readonly generateFlashcardsApiV1ProjectsProjectIdFlashcardGroupsGroupIdGeneratePost: (
    projectId: string,
    groupId: string,
    options: typeof GenerateRequest.Encoded,
  ) => Effect.Effect<
    typeof FlashcardGroupDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Queue flashcard generation request with streaming progress updates.
   */
  readonly generateFlashcardsStreamApiV1ProjectsProjectIdFlashcardGroupsGroupIdGenerateStreamPost: (
    projectId: string,
    groupId: string,
    options: typeof GenerateRequest.Encoded,
  ) => Effect.Effect<
    typeof GenerateFlashcardsStreamApiV1ProjectsProjectIdFlashcardGroupsGroupIdGenerateStreamPost200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all flashcards in a group.
   */
  readonly listFlashcardsApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsGet: (
    projectId: string,
    groupId: string,
  ) => Effect.Effect<
    typeof ListFlashcardsApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a new flashcard in a group.
   */
  readonly createFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsPost: (
    projectId: string,
    groupId: string,
    options: typeof FlashcardCreate.Encoded,
  ) => Effect.Effect<
    typeof FlashcardDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a flashcard by ID.
   */
  readonly getFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsFlashcardIdGet: (
    projectId: string,
    groupId: string,
    flashcardId: string,
  ) => Effect.Effect<
    typeof FlashcardDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a flashcard.
   */
  readonly deleteFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsFlashcardIdDelete: (
    projectId: string,
    groupId: string,
    flashcardId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Update a flashcard.
   */
  readonly updateFlashcardApiV1ProjectsProjectIdFlashcardGroupsGroupIdFlashcardsFlashcardIdPatch: (
    projectId: string,
    groupId: string,
    flashcardId: string,
    options: typeof FlashcardUpdate.Encoded,
  ) => Effect.Effect<
    typeof FlashcardDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Record which cards the student knew, for SLO mastery.
   */
  readonly submitFlashcardAttemptApiV1ProjectsProjectIdFlashcardGroupsGroupIdAttemptsPost: (
    projectId: string,
    groupId: string,
    options: typeof FlashcardAttemptCreate.Encoded,
  ) => Effect.Effect<
    typeof FlashcardAttemptDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * The student's most recent run through this flashcard set, if any.
   */
  readonly getLatestFlashcardAttemptApiV1ProjectsProjectIdFlashcardGroupsGroupIdAttemptsLatestGet: (
    projectId: string,
    groupId: string,
  ) => Effect.Effect<
    typeof FlashcardAttemptStateDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List practice records for a project.
   */
  readonly listPracticeRecordsApiV1ProjectsProjectIdPracticeRecordsGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListPracticeRecordsApiV1ProjectsProjectIdPracticeRecordsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create a single practice record.
   */
  readonly createPracticeRecordApiV1ProjectsProjectIdPracticeRecordsPost: (
    projectId: string,
    options: typeof PracticeRecordCreate.Encoded,
  ) => Effect.Effect<
    typeof PracticeRecordDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Create multiple practice records.
   */
  readonly createPracticeRecordsBatchApiV1ProjectsProjectIdPracticeRecordsBatchPost: (
    projectId: string,
    options: typeof PracticeRecordBatchCreate.Encoded,
  ) => Effect.Effect<
    typeof CreatePracticeRecordsBatchApiV1ProjectsProjectIdPracticeRecordsBatchPost201.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all mind maps for a project.
   */
  readonly listMindMapsApiV1ProjectsProjectIdMindMapsGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListMindMapsApiV1ProjectsProjectIdMindMapsGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Generate/create a mind map.
   *
   * Note: AI generation is not yet implemented in edu-shared service.
   * This endpoint creates a basic mind map structure.
   */
  readonly createMindMapApiV1ProjectsProjectIdMindMapsPost: (
    projectId: string,
    options: typeof MindMapCreate.Encoded,
  ) => Effect.Effect<
    typeof MindMapDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get a mind map by ID.
   */
  readonly getMindMapApiV1ProjectsProjectIdMindMapsMindMapIdGet: (
    projectId: string,
    mindMapId: string,
  ) => Effect.Effect<
    typeof MindMapDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a mind map.
   */
  readonly deleteMindMapApiV1ProjectsProjectIdMindMapsMindMapIdDelete: (
    projectId: string,
    mindMapId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Queue mind map generation request with streaming progress updates.
   */
  readonly createMindMapStreamApiV1ProjectsProjectIdMindMapsStreamPost: (
    projectId: string,
    options: typeof MindMapCreate.Encoded,
  ) => Effect.Effect<
    typeof CreateMindMapStreamApiV1ProjectsProjectIdMindMapsStreamPost200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get the latest study plan for the user in the project.
   */
  readonly getLatestStudyPlanApiV1ProjectsProjectIdStudyPlansLatestGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof GetLatestStudyPlanApiV1ProjectsProjectIdStudyPlansLatestGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all study plans for the user in the project.
   */
  readonly listStudyPlansApiV1ProjectsProjectIdStudyPlansGet: (
    projectId: string,
  ) => Effect.Effect<
    typeof ListStudyPlansApiV1ProjectsProjectIdStudyPlansGet200.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Generate a new study plan for the user based on performance.
   */
  readonly generateStudyPlanApiV1ProjectsProjectIdStudyPlansGeneratePost: (
    projectId: string,
  ) => Effect.Effect<
    typeof StudyPlanDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Get current usage statistics for the authenticated user
   */
  readonly getUsageApiV1UsageGet: () => Effect.Effect<
    typeof UsageDto.Type,
    HttpClientError.HttpClientError | ParseError
  >
  /**
   * Get a user by ID.
   */
  readonly getUserApiV1UsersUserIdGet: (
    userId: string,
  ) => Effect.Effect<
    typeof UserDto.Type,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * Delete a user.
   */
  readonly deleteUserApiV1UsersUserIdDelete: (
    userId: string,
  ) => Effect.Effect<
    void,
    | HttpClientError.HttpClientError
    | ParseError
    | ClientError<'HTTPValidationError', typeof HTTPValidationError.Type>
  >
  /**
   * List all users.
   */
  readonly listUsersApiV1UsersGet: () => Effect.Effect<
    typeof ListUsersApiV1UsersGet200.Type,
    HttpClientError.HttpClientError | ParseError
  >
  /**
   * Get authenticated user information (requires auth)
   */
  readonly getCurrentUserInfoApiV1AuthMeGet: () => Effect.Effect<
    typeof UserDto.Type,
    HttpClientError.HttpClientError | ParseError
  >
}

export interface ClientError<Tag extends string, E> {
  readonly _tag: Tag
  readonly request: HttpClientRequest.HttpClientRequest
  readonly response: HttpClientResponse.HttpClientResponse
  readonly cause: E
}

class ClientErrorImpl extends Data.Error<{
  _tag: string
  cause: any
  request: HttpClientRequest.HttpClientRequest
  response: HttpClientResponse.HttpClientResponse
}> {}

export const ClientError = <Tag extends string, E>(
  tag: Tag,
  cause: E,
  response: HttpClientResponse.HttpClientResponse,
): ClientError<Tag, E> =>
  new ClientErrorImpl({
    _tag: tag,
    cause,
    response,
    request: response.request,
  }) as any
