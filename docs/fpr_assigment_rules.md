# FPR Assignment Rules

## Purpose

Assign newly discovered startups to FPRs for outreach and relationship management.

## Assignment Method

Current Method:
- Round Robin

Primary Owner:
- FPR1

Secondary Owner:
- FPR2

## Mapping Source

Use:

docs/fpr_assignment_mapping.json

## Assignment Logic

1. When a startup is inserted:
   - Check if already assigned.
   - If not assigned:
     - Pick next FPR1 in round-robin order.
     - Assign corresponding FPR2.

2. Store assignment in:

startup_assignments

Columns:

- startup_id
- assigned_fpr1
- assigned_fpr2
- assignment_date
- assignment_status

## Future Enhancements

Assignment may later be based on:
- Sector expertise
- Geography
- Startup stage
- BFSI relevance score
- Existing portfolio load