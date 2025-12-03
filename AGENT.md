# Pass-Man Agent Context

## 1. Project Overview

Pass-Man is an enterprise password management system designed for organizations. It focuses on security (AES-256-GCM, zero-trust), privacy, and group-based collaboration.

- **Goal**: Secure, scalable, and user-friendly password management.
- **Target Audience**: SMEs (50-500 employees).

## 2. Key Resources

- **Master Spec**: `docs/SRS.md`
- **Product Requirements**: `docs/PRD.md`
- **Backlog**: `docs/BACKLOG.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Coding Standards**: `docs/CODING_STANDARDS.md`
- **Developer Guide**: `docs/DEVELOPER_GUIDE.md`

## 3. Technology Stack

- **Backend**: Django 5.x + Django REST Framework
- **Frontend**: HTMX + Alpine.js (Interactive components), Tailwind CSS + Shadcn (Styling)
- **Database**: PostgreSQL
- **Infrastructure**: Docker, Docker Compose
- **Security**: AES-256-GCM, JWT

## 4. Current Status

- **Completed**:
  - **Epic 1**: Project Foundation & Setup ✅
  - **Epic 2**: Authentication & User Management ✅
  - **Epic 3**: Group Management System ✅
- **In Progress / Next Up**:
  - **Epic 4**: Password Management Core (CRUD, Encryption, Search) �
  - **Epic 5**: Directory Organization (Planned)
  - **Epic 6**: Password Sharing & Collaboration (Planned)

## 5. Development Guidelines

- **Code Style**: Follow `docs/CODING_STANDARDS.md`.
- **Workflow**:
  1. Check `docs/BACKLOG.md` for tasks.
  2. Implement features using Django + HTMX patterns.
  3. Update documentation as needed.
- **Testing**: Ensure unit tests cover critical paths (90%+ coverage target).

## 6. Agent Instructions

- **Context Awareness**: Always check `docs/BACKLOG.md` and `docs/PRD.md` to understand the current priorities and requirements.
- **Architecture Compliance**: Adhere to the architecture defined in `docs/ARCHITECTURE.md`, specifically the Django + HTMX + Alpine integration.
- **Security First**: Prioritize security in all code changes. Do not expose sensitive data.
- **Documentation**: Keep `AGENT.md` updated if there are major shifts in project scope or status.
