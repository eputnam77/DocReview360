"""Central message templates for audit logs."""

from datetime import datetime, timezone

MESSAGES = {
    "create_project": (
        "{user} created project {project_id} on {date} at {time}"
    ),
    "selected_document_type_for_project_on": (
        "{user} selected document type '{document_type}' for project {project_id} on "
        "{date}"
    ),
    "ai_validation_confirmed_as_appropriate_for_project_on": (
        "AI validation confirmed '{document_type}' as appropriate for project "
        "{project_id} on {date}"
    ),
    "project_assigned_to_phase_by_on": (
        "Project {project_id} assigned to phase '{phase_name}' by {user} on {date}"
    ),
    "upload_file": (
        "{user} uploaded file '{filename}' to project {project_id} on {date}"
    ),
    "applied_template_to_project_on": (
        "{user} applied template '{template_name}' to project {project_id} on {date}"
    ),
    "saved_draft_version_of_project_on": (
        "{user} saved draft version {version} of project {project_id} on {date}"
    ),
    "submitted_project_for_review_on": (
        "{user} submitted project {project_id} for review on {date}"
    ),
    "assigned_as_reviewer_for_project_on": (
        "{user} assigned {reviewer} as reviewer for project {project_id} on {date}"
    ),
    "sent_document_to_for_review_on": (
        "{user} sent document {project_id} to {reviewer} for review on {date}"
    ),
    "system_sent_review_notification_to_for_project_on": (
        "System sent review notification to {reviewer} for project {project_id} on {date}"
    ),
    "accepted_review_assignment_for_project_on": (
        "{reviewer} accepted review assignment for project {project_id} on {date}"
    ),
    "declined_review_assignment_for_project_on": (
        "{reviewer} declined review assignment for project {project_id} on {date}"
    ),
    "reassigned_project_from_to_on": (
        "{user} reassigned project {project_id} from {old_reviewer} to {new_reviewer} on "
        "{date}"
    ),
    "system_sent_follow_up_reminder_to_for_project_on": (
        "System sent follow-up reminder to {reviewer} for project {project_id} on {date}"
    ),
    "system_sent_escalation_notification_to_for_overdue_project_on": (
        "System sent escalation notification to {manager} for overdue project "
        "{project_id} on {date}"
    ),
    "concurred_with_draft_on_at": (
        "{reviewer} concurred with draft {project_id} on {date} at {time}"
    ),
    "approved_document_with_digital_signature_on": (
        "{reviewer} approved document {project_id} with digital signature on {date}"
    ),
    "rejected_draft_with_comments_on": (
        "{reviewer} rejected draft {project_id} with comments on {date}"
    ),
    "requested_re_review_for_project_on": (
        "{reviewer} requested re-review for project {project_id} on {date}"
    ),
    "provided_non_concurrence_for_project_on": (
        "{reviewer} provided non-concurrence for project {project_id} on {date}"
    ),
    "digital_signature_verification_passed_for_on_project_on": (
        "Digital signature verification passed for {reviewer} on project {project_id} on "
        "{date}"
    ),
    "all_required_approvals_completed_for_project_on": (
        "All required approvals completed for project {project_id} on {date}"
    ),
    "phase_completion_achieved_for_project_on": (
        "Phase completion achieved for project {project_id} on {date}"
    ),
    "made_changes_to_project_on": (
        "{user} made changes to project {project_id} on {date}"
    ),
    "added_comment_to_project_on": (
        "{user} added comment to project {project_id} on {date}"
    ),
    "responded_to_comment_on_project_on": (
        "{user} responded to comment on project {project_id} on {date}"
    ),
    "accepted_suggested_changes_for_project_on": (
        "{user} accepted suggested changes for project {project_id} on {date}"
    ),
    "rejected_suggested_changes_for_project_on": (
        "{user} rejected suggested changes for project {project_id} on {date}"
    ),
    "ai_assistant_provided_suggestions_for_project_on": (
        "AI assistant provided suggestions for project {project_id} on {date}"
    ),
    "used_ai_assistance_for_project_on": (
        "{user} used AI assistance for project {project_id} on {date}"
    ),
    "document_validation_completed_for_project_on": (
        "Document validation completed for project {project_id} on {date}"
    ),
    "import_docx": (
        "{user} imported DOCX file '{filename}' to project {project_id} on {date}"
    ),
    "convert_tiptap": (
        "System converted DOCX to TipTap format for project {project_id} on {date}"
    ),
    "system_applied_template_during_conversion_for_project_on": (
        "System applied template '{template_name}' during conversion for project "
        "{project_id} on {date}"
    ),
    "system_inserted_placeholder_heading_in_project_on": (
        "System inserted placeholder heading in project {project_id} on {date}"
    ),
    "tiptap_content_saved_to_cms_for_project_on": (
        "TipTap content saved to CMS for project {project_id} on {date}"
    ),
    "converted_project_from_to_on": (
        "{user} converted project {project_id} from '{old_type}' to '{new_type}' on "
        "{date}"
    ),
    "system_applied_new_template_for_project_on": (
        "System applied new template for project {project_id} on {date}"
    ),
    "added_document_number_to_project_on": (
        "{user} added document number '{doc_number}' to project {project_id} on {date}"
    ),
    "set_priority_to_for_project_on": (
        "{user} set priority to '{priority_level}' for project {project_id} on {date}"
    ),
    "increased_priority_for_project_on": (
        "{user} increased priority for project {project_id} on {date}"
    ),
    "decreased_priority_for_project_on": (
        "{user} decreased priority for project {project_id} on {date}"
    ),
    "system_sent_priority_notification_for_project_on": (
        "System sent priority notification for project {project_id} on {date}"
    ),
    "system_escalated_high_priority_project_to_on": (
        "System escalated high-priority project {project_id} to {manager} on {date}"
    ),
    "created_temporary_assignment_for_project_from_to_on": (
        "{user} created temporary assignment for project {project_id} from {start_date} "
        "to {end_date} on {date}"
    ),
    "temporarily_reassigned_project_from_to_on": (
        "{user} temporarily reassigned project {project_id} from {original_user} to "
        "{temp_user} on {date}"
    ),
    "temporary_assignment_ended_for_project_on": (
        "Temporary assignment ended for project {project_id} on {date}"
    ),
    "system_reverted_project_to_on": (
        "System reverted project {project_id} to {original_user} on {date}"
    ),
    "extended_temporary_assignment_for_project_until_on": (
        "{user} extended temporary assignment for project {project_id} until "
        "{new_end_date} on {date}"
    ),
    "added_new_document_type_to_system_on": (
        "{admin} added new document type '{document_type}' to system on {date}"
    ),
    "created_template_for_document_type_on": (
        "{admin} created template for document type '{document_type}' on {date}"
    ),
    "configured_workflow_for_document_type_on": (
        "{admin} configured workflow for document type '{document_type}' on {date}"
    ),
    "set_validation_rules_for_document_type_on": (
        "{admin} set validation rules for document type '{document_type}' on {date}"
    ),
    "system_applied_new_document_type_configuration_to_existing_projects_on": (
        "System applied new document type configuration to existing projects on {date}"
    ),
    "searched_for_projects_with_criteria_on": (
        "{user} searched for projects with criteria '{search_terms}' on {date}"
    ),
    "saved_search_query_on": (
        "{user} saved search query '{query_name}' on {date}"
    ),
    "exported_search_results_for_on": (
        "{user} exported search results for '{search_criteria}' on {date}"
    ),
    "accessed_personal_assignment_dashboard_on": (
        "{user} accessed personal assignment dashboard on {date}"
    ),
    "viewed_role_based_assignment_report_for_on": (
        "{user} viewed role-based assignment report for '{role}' on {date}"
    ),
    "customized_dashboard_widgets_on": (
        "{user} customized dashboard widgets on {date}"
    ),
    "exported_dashboard_data_in_format_on": (
        "{user} exported dashboard data in {format} format on {date}"
    ),
    "system_generated_workload_analytics_report_on": (
        "System generated workload analytics report on {date}"
    ),
    "system_identified_workflow_bottleneck_in_on": (
        "System identified workflow bottleneck in {process} on {date}"
    ),
    "system_generated_capacity_planning_report_on": (
        "System generated capacity planning report on {date}"
    ),
    "system_detected_stalled_project_no_status_change_in_2_weeks_on": (
        "System detected stalled project {project_id} - no status change in 2 weeks on "
        "{date}"
    ),
    "system_added_status_update_for_stalled_project_on": (
        "System added status update for stalled project {project_id} on {date}"
    ),
    "system_sent_stalled_project_notification_to_for_project_on": (
        "System sent stalled project notification to {manager} for project {project_id} "
        "on {date}"
    ),
    "api_endpoint_accessed_for_project_status_data_on": (
        "API endpoint accessed for project status data on {date}"
    ),
    "external_dashboard_integrated_project_status_data_on": (
        "External dashboard integrated project status data on {date}"
    ),
    "project_transitioned_from_to_on": (
        "Project {project_id} transitioned from '{old_phase}' to '{new_phase}' on {date}"
    ),
    "initiated_phase_transition_for_project_on": (
        "{user} initiated phase transition for project {project_id} on {date}"
    ),
    "phase_completion_requirements_met_for_project_on": (
        "Phase completion requirements met for project {project_id} on {date}"
    ),
    "public_comment_period_started_for_project_on": (
        "Public comment period started for project {project_id} on {date}"
    ),
    "public_comment_period_ended_for_project_on": (
        "Public comment period ended for project {project_id} on {date}"
    ),
    "final_issuance_phase_initiated_for_project_on": (
        "Final issuance phase initiated for project {project_id} on {date}"
    ),
    "system_automatically_saved_project_on": (
        "System automatically saved project {project_id} on {date}"
    ),
    "system_generated_project_number_on": (
        "System generated project number {project_id} on {date}"
    ),
    "system_applied_default_reviewers_to_project_on": (
        "System applied default reviewers to project {project_id} on {date}"
    ),
    "system_detected_significant_changes_in_project_on": (
        "System detected significant changes in project {project_id} on {date}"
    ),
    "system_triggered_re_review_requirement_for_project_on": (
        "System triggered re-review requirement for project {project_id} on {date}"
    ),
    "system_sent_automated_notification_to_for_project_on": (
        "System sent automated notification to {user} for project {project_id} on {date}"
    ),
    "system_archived_project_on": (
        "System archived project {project_id} on {date}"
    ),
    "system_generated_approval_report_for_project_on": (
        "System generated approval report for project {project_id} on {date}"
    ),
    "exported_project_in_format_on": (
        "{user} exported project {project_id} in {format} format on {date}"
    ),
    "system_generated_export_for_project_on": (
        "System generated {format} export for project {project_id} on {date}"
    ),
    "export_validation_completed_for_project_on": (
        "Export validation completed for project {project_id} on {date}"
    ),
    "system_archived_project_in_on": (
        "System archived project {project_id} in {archive_format} on {date}"
    ),
    "archive_metadata_generated_for_project_on": (
        "Archive metadata generated for project {project_id} on {date}"
    ),
    "compliance_documentation_created_for_project_on": (
        "Compliance documentation created for project {project_id} on {date}"
    ),
    "error_occurred_during_export_generation_for_project_on": (
        "Error occurred during export generation for project {project_id} on {date}: "
        "{error_message}"
    ),
    "validation_failed_for_project_on": (
        "Validation failed for project {project_id} on {date}: {validation_errors}"
    ),
    "digital_signature_verification_failed_for_on_project_on": (
        "Digital signature verification failed for {reviewer} on project {project_id} on "
        "{date}"
    ),
    "system_timeout_occurred_during_document_processing_for_project_on": (
        "System timeout occurred during document processing for project {project_id} on "
        "{date}"
    ),
    "permission_denied_for_attempting_to_access_project_on": (
        "Permission denied for {user} attempting to access project {project_id} on {date}"
    ),
    "document_processing_completed_for_project_in_ms_on": (
        "Document processing completed for project {project_id} in {duration}ms on {date}"
    ),
    "export_generation_completed_for_project_in_ms_on": (
        "Export generation completed for project {project_id} in {duration}ms on {date}"
    ),
    "system_performance_metrics_recorded_for_project_on": (
        "System performance metrics recorded for project {project_id} on {date}"
    ),
    "database_query_optimization_applied_for_project_on": (
        "Database query optimization applied for project {project_id} on {date}"
    ),
    "login": (
        "{user} logged into system on {date} from {ip_address}"
    ),
    "logged_out_of_system_on": (
        "{user} logged out of system on {date}"
    ),
    "accessed_project_on": (
        "{user} accessed project {project_id} on {date}"
    ),
    "failed_login_attempt_for_from_on": (
        "Failed login attempt for {username} from {ip_address} on {date}"
    ),
    "session_timeout_for_on": (
        "Session timeout for {user} on {date}"
    ),
    "permission_escalation_request_for_on_project_on": (
        "Permission escalation request for {user} on project {project_id} on {date}"
    ),
}


def render(name: str, **data: str) -> str:
    """Return a formatted message by name."""
    template = MESSAGES.get(name, name)
    now = datetime.now(timezone.utc)
    data.setdefault("date", now.strftime("%Y-%m-%d"))
    data.setdefault("time", now.strftime("%H:%M"))
    # avoid KeyError for optional placeholders like IP address
    data.setdefault("ip_address", "unknown")
    return template.format(**data)
