# Development Workflow

## Overview

This document outlines the standard development workflow for this project.

## Workflow Steps

### 1. Planning Phase
- Detail the task and understand requirements
- Explore the codebase to find relevant files and patterns
- Design the best implementation approach

### 2. GitHub Issue Creation
Create an issue using `gh` CLI containing:
- **Implementation Plan**: Detailed steps for the implementation
- **E2E Testing Strategy**: How the feature will be tested end-to-end
- **Acceptance Criteria**: Clear criteria that must be met for completion

The issue is our **source of truth** for the task.

### 3. Branch Workflow
```bash
# Pull latest from development branch
git checkout development
git pull origin development

# Create a new feature branch
git checkout -b <feature-branch-name>
```

### 4. Implementation
- Work on the implementation following the plan
- Periodically update the GitHub issue with progress
- Continue until all tests pass and acceptance criteria are met

### 5. Pull Request & Closure
- Create a PR into the `development` branch
- Update the GitHub issue state
- Link the PR to the issue

## Progress Tracking

Always keep the GitHub issue updated with:
- Current status
- Completed items
- Blockers or changes to the plan
