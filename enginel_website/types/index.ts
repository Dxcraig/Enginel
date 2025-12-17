/**
 * TypeScript types for Enginel API models
 */

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_us_person: boolean;
  security_clearance_level: 'UNCLASSIFIED' | 'CONFIDENTIAL' | 'SECRET' | 'TOP_SECRET';
  organization: string;
  phone_number?: string;
  department?: string;
  job_title?: string;
  date_joined: string;
}

export interface DesignSeries {
  id: string;
  part_number: string;
  name: string;
  description?: string;
  status: 'DRAFT' | 'IN_REVIEW' | 'RELEASED' | 'OBSOLETE';
  lifecycle_state?: string;
  classification_level: string;
  requires_itar_compliance: boolean;
  version_count: number;
  current_version?: string;
  latest_version_number: number;
  created_by_username: string;
  created_at: string;
  updated_at: string;
}

export interface DesignAsset {
  id: string;
  series: string | { id: string; part_number: string };
  version_number: number;
  version_label?: string;
  filename: string;
  file_name?: string;
  file_size: number;
  file_hash: string;
  file_type: string;
  file_url?: string;
  s3_key?: string;
  status: 'UPLOADING' | 'PROCESSING' | 'READY' | 'FAILED';
  processing_status?: string;
  processing_error?: string;
  classification: string;
  is_itar_controlled: boolean;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
  change_description?: string;
  notes?: string;
}

export interface ValidationRule {
  id: string;
  name: string;
  description: string;
  rule_type: 'REGEX' | 'RANGE' | 'LENGTH' | 'FORMAT' | 'CUSTOM' | 'FILE_TYPE' | 'FILE_SIZE' | 'UNIQUENESS' | 'RELATIONSHIP' | 'BUSINESS_RULE';
  target_model: 'DesignAsset' | 'DesignSeries' | 'CustomUser' | 'ReviewSession' | 'Markup' | 'AssemblyNode' | '*';
  target_field: string;
  rule_config: any;
  error_message: string;
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  is_active: boolean;
  apply_on_create: boolean;
  apply_on_update: boolean;
  total_checks?: number;
  total_failures?: number;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

export interface ValidationResult {
  id: string;
  rule: ValidationRule | string;
  target_model: string;
  target_id: string;
  target_field?: string;
  status: 'PASSED' | 'FAILED' | 'SKIPPED' | 'ERROR';
  error_message?: string;
  details?: any;
  was_blocked: boolean;
  was_overridden?: boolean;
  validated_at: string;
  validated_by?: string;
}

export interface ReviewSession {
  id: string;
  design_asset: string;
  title?: string;
  description?: string;
  status: 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
  created_by: string;
  created_by_username?: string;
  reviewers?: string[];
  reviewer_usernames?: string[];
  markup_count?: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  // Detail view extras
  markups?: Markup[];
  design_asset_detail?: DesignAsset;
}

export interface Markup {
  id: string;
  review_session: string;
  author: string;
  author_username?: string;
  title: string;
  comment: string;
  anchor_point: { x: number; y: number; z: number };
  camera_state: {
    position: { x: number; y: number; z: number };
    target: { x: number; y: number; z: number };
    up: { x: number; y: number; z: number };
  };
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssemblyNode {
  id: string;
  component_name: string;
  part_number?: string;
  node_type: 'assembly' | 'part';
  quantity?: number;
  reference_designator?: string;
  children?: AssemblyNode[];
}

export interface AuditLogEntry {
  id: string;
  actor_id: number;
  actor_username: string;
  action: 'CREATE' | 'READ' | 'UPDATE' | 'DELETE' | 'DOWNLOAD' | 'UPLOAD';
  action_display: string;
  resource_type: string;
  resource_id: string;
  ip_address?: string;
  user_agent?: string;
  changes?: Record<string, any>;
  timestamp: string;
}

export interface Notification {
  id: string;
  recipient: string;
  recipient_username?: string;
  notification_type: 'DESIGN_UPLOADED' | 'DESIGN_APPROVED' | 'DESIGN_REJECTED' | 'DESIGN_UPDATED' |
  'REVIEW_ASSIGNED' | 'REVIEW_STARTED' | 'REVIEW_COMPLETED' | 'REVIEW_COMMENT' |
  'MARKUP_ADDED' | 'MARKUP_RESOLVED' | 'MENTION' | 'VALIDATION_FAILED' |
  'VALIDATION_PASSED' | 'JOB_COMPLETED' | 'JOB_FAILED' | 'SYSTEM_ALERT' | 'SECURITY_ALERT';
  title: string;
  message: string;
  resource_type?: string;
  resource_id?: string;
  action_url?: string;
  actor?: string;
  actor_username?: string;
  actor_email?: string;
  is_read: boolean;
  is_archived: boolean;
  read_at?: string;
  archived_at?: string;
  priority: 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  is_expired?: boolean;
  time_ago?: string;
}
