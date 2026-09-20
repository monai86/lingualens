"""Interactive 5-step clinical workflow controller for LinguaLens TUI."""

from __future__ import annotations

import os
from typing import Any
from rich.console import Console
from rich.prompt import Prompt, Confirm

from packages.tui.client import (
    LinguaLensClient,
    LinguaLensApiError,
    LinguaLensAuthError,
    LinguaLensPermissionError,
    LinguaLensConflictError,
)
from packages.tui.ui import (
    console,
    print_banner,
    render_cases_table,
    render_sessions_table,
    render_transcript_review_table,
    render_findings_view,
    render_report_view,
    render_children_table,
)


class WorkflowRunner:
    """Controls the interactive text-based session navigation."""

    def __init__(self, client: LinguaLensClient):
        self.client = client
        self.active_case_id: str | None = None
        self.active_session_id: str | None = None
        self.active_transcript: dict[str, Any] | None = None
        self.active_report: dict[str, Any] | None = None
        self.current_mode: str = "legacy"
        # Assessment V2 context state
        self.active_child_id: str | None = None
        self.active_child: dict[str, Any] | None = None
        self.active_consent: dict[str, Any] | None = None
        self.active_assessment_id: str | None = None
        self.active_assessment: dict[str, Any] | None = None

    def _handle_auth_error(self, error: Exception) -> None:
        """Handle HTTP 401 auth invalidation: wipe credentials and all sensitive clinical context."""
        if hasattr(self.client, "clear_session"):
            self.client.clear_session()
        self.active_case_id = None
        self.active_session_id = None
        self.active_transcript = None
        self.active_report = None
        self.active_child_id = None
        self.active_child = None
        self.active_consent = None
        self.active_assessment_id = None
        self.active_assessment = None

    def _set_active_child(self, child_id: str | None) -> None:
        """Switch active child, flushing previous legacy clinical context."""
        self.current_mode = "v2"
        self.active_case_id = None
        self.active_session_id = None
        self.active_transcript = None
        self.active_report = None

        self.active_child_id = None
        self.active_child = None
        self.active_consent = None
        self.active_assessment_id = None
        self.active_assessment = None

        if not child_id:
            return

        from packages.tui.client import LinguaLensAuthError, LinguaLensPermissionError
        try:
            self.active_child = self.client.get_child(child_id)
            self.active_child_id = child_id
        except LinguaLensAuthError as exc:
            console.print(f"\n[bold red]🔒 Authentication Error: {exc}[/bold red]")
            self._handle_auth_error(exc)
        except LinguaLensPermissionError as exc:
            console.print(f"\n[bold red]⛔ Permission Denied: {exc}[/bold red]")
        except Exception as exc:
            console.print(f"\n[bold red]⚠️ Failed to load child: {exc}[/bold red]")

    def _set_active_case(self, case_id: str | None) -> None:
        """Switch active case, flushing previous V2 clinical context."""
        self.current_mode = "legacy"
        self.active_child_id = None
        self.active_child = None
        self.active_consent = None
        self.active_assessment_id = None
        self.active_assessment = None

        self.active_case_id = case_id
        self.active_session_id = None
        self.active_transcript = None
        self.active_report = None


    def start(self, initial_case_id: str | None = None) -> None:
        """Main interaction loop with unified error boundary."""
        if initial_case_id:
            self.active_case_id = initial_case_id
        if self.active_case_id and self.active_session_id:
            route = "session_workspace"
        elif self.active_case_id:
            route = "sessions"
        elif self.active_child_id:
            route = "children"
        else:
            route = "entry"

        while True:
            console.clear()
            is_online = self.client.check_health()
            print_banner(api_online=is_online, current_step=self._get_current_step_name())

            try:
                if route == "entry":
                    route = self._entry_menu()
                    if route == "exit":
                        console.print("[yellow]Exiting LinguaLens TUI. Goodbye![/yellow]")
                        break
                elif route == "cases":
                    action = self._cases_menu()
                    if action == "exit":
                        console.print("[yellow]Exiting LinguaLens TUI. Goodbye![/yellow]")
                        break
                    elif action == "back":
                        route = "entry"
                    elif action == "children":
                        route = "children"
                    elif self.active_case_id:
                        route = "sessions"
                elif route == "children":
                    action = self._children_menu()
                    if action == "exit":
                        console.print("[yellow]Exiting LinguaLens TUI. Goodbye![/yellow]")
                        break
                    elif action == "back":
                        route = "entry"
                elif not self.active_session_id:
                    action = self._sessions_menu()
                    if action == "back":
                        self.active_case_id = None
                        route = "cases"
                    elif action == "exit":
                        break
                else:
                    action = self._session_workspace_menu()
                    if action == "back":
                        self.active_session_id = None
                        self.active_transcript = None
                    elif action == "exit":
                        break
            except LinguaLensAuthError as exc:
                console.print(f"\n[bold red]🔒 Authentication Error: {exc}[/bold red]")
                console.print("[yellow]Session expired or invalid credentials. Please re-authenticate or sign-in again.[/yellow]")
                self._handle_auth_error(exc)
                route = "entry"
                action = Prompt.ask("Press Enter to continue, or [Q] to quit", default="")
                if action.lower() in ("q", "quit", "exit"):
                    break
            except LinguaLensPermissionError as exc:
                console.print(f"\n[bold red]⛔ Permission Denied: {exc}[/bold red]")
                console.print("[yellow]You do not have permission to access this resource. Active session preserved.[/yellow]")
                route = "entry"
                action = Prompt.ask("Press Enter to continue, or [Q] to quit", default="")
                if action.lower() in ("q", "quit", "exit"):
                    break
            except LinguaLensApiError as exc:
                console.print(f"\n[bold red]⚠️ API Error: {exc}[/bold red]")
                choice = Prompt.ask("Choose action: [R]etry / Continue, [B]ack to Main, or [Q]uit", default="b")
                if choice.lower() in ("q", "quit", "exit"):
                    break
                elif choice.lower() in ("b", "back"):
                    route = "entry"

    def _entry_menu(self) -> str:
        """Top-level entry menu choosing workflow before invoking legacy APIs."""
        console.print("\n[bold cyan]Select Directory / Workflow:[/bold cyan]")
        console.print("  [C] [bold yellow]C[/bold yellow]hild Directory (Assessment V2 - Canonical)")
        console.print("  [1] [bold green]1[/bold green] Legacy Cases Directory")
        console.print("  [Q] [bold red]Q[/bold red]uit")

        choice = Prompt.ask("\nChoose an option", default="1")
        if choice.lower() in ("q", "quit", "exit"):
            return "exit"
        if choice.lower() == "c":
            return "children"
        return "cases"

    def _get_current_step_name(self) -> str:
        if self.active_assessment_id:
            return f"Assessment: {self.active_assessment_id} (Child: {self.active_child_id})"
        if self.active_child_id:
            return f"Child: {self.active_child_id} (Assessment V2)"
        if not self.active_case_id:
            return "Cases Directory"
        if not self.active_session_id:
            return f"Case: {self.active_case_id} > Sessions"
        return f"Session Workspace ({self.active_session_id})"

    # --- Step 1: Cases Menu ---
    def _cases_menu(self) -> str:
        cases = self.client.list_cases()
        render_cases_table(cases)

        console.print("\n[bold cyan]Actions:[/bold cyan]")
        if cases:
            console.print("  [1-N] Select Case Number")
        console.print("  [N]   Create [bold green]N[/bold green]ew Case")
        console.print("  [B]   [bold blue]B[/bold blue]ack")
        console.print("  [Q]   [bold red]Q[/bold red]uit")

        choice = Prompt.ask("\nChoose an option", default="1")
        if choice.lower() in ("q", "quit", "exit"):
            return "exit"
        if choice.lower() in ("b", "back"):
            return "back"
        if choice.lower() == "n":
            self._create_case_wizard()
            return "sessions" if self.active_case_id else "stay"

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(cases):
                self._set_active_case(cases[idx]["case_id"])
                return "sessions"
        except ValueError:
            pass

        console.print("[red]Invalid selection.[/red]")
        Prompt.ask("Press Enter to continue")
        return "stay"

    def _create_case_wizard(self) -> None:
        console.print("\n[bold green]➕ Create New Case[/bold green]")
        child_code = Prompt.ask("Child Identifier / Code", default="C-0201")
        age_str = Prompt.ask("Child Age in Months", default="36")
        lang = Prompt.ask("Primary Language (th/en)", default="th")
        notes = Prompt.ask("Clinical Notes", default="Initial evaluation for speech delay.")

        try:
            age = int(age_str)
        except ValueError:
            console.print("[red]Invalid age format.[/red]")
            Prompt.ask("Press Enter to continue")
            return

        if not 0 <= age <= 240:
            console.print("[red]Age in months must be between 0 and 240.[/red]")
            Prompt.ask("Press Enter to continue")
            return

        try:
            new_case = self.client.create_case(
                child_code=child_code,
                age_months=age,
                language=lang,
                notes=notes,
            )
        except (LinguaLensAuthError, LinguaLensPermissionError):
            raise
        except LinguaLensApiError as exc:
            console.print(f"[bold red]⚠️ Failed to create case: {exc}[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        try:
            case_id = new_case["case_id"]
        except (KeyError, TypeError):
            console.print("[bold red]⚠️ Failed to create case: API response missing case_id.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        console.print(f"[bold green]✓ Case created successfully: {case_id}[/bold green]")
        self._set_active_case(case_id)
        Prompt.ask("Press Enter to continue")

    def _resolve_consent_state(
        self,
        child_id: str,
        purpose: str = "clinical_assessment",
    ) -> tuple[str, dict[str, Any] | None]:
        """Query authoritative consent history and resolve current state using latest-version-per-purpose."""
        try:
            history = self.client.list_consents(child_id)
        except (LinguaLensAuthError, LinguaLensPermissionError):
            raise
        except Exception:
            return "error", None

        matching = [c for c in history if c.get("purpose") == purpose]
        if not matching:
            return "no-record", None
        latest = max(matching, key=lambda c: c.get("version", 0))
        st = latest.get("status")
        if st == "active":
            return "active", latest
        elif st == "withdrawn":
            return "withdrawn", latest
        return st or "unknown", latest

    def _record_consent_wizard(self) -> None:
        """Prompt clinician for explicit consent recording on the active child profile."""
        if not self.active_child_id:
            console.print("[bold red]Please select an active child first.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        child_code = self.active_child.get("display_code", self.active_child_id) if self.active_child else self.active_child_id
        console.print(f"\n[bold yellow]📋 Record Parental / Guardian Consent[/bold yellow]")
        console.print(f"Child Profile: [cyan]{child_code}[/cyan] ({self.active_child_id})")
        console.print("Purpose: [bold]clinical_assessment[/bold]")

        console.print("\nNotice: This action records official consent received from or withdrawn by")
        console.print("the child's parent/guardian. Confirming documents authorized clinician recording.")

        console.print("\nSelect Consent Action:")
        console.print("  [1] Grant [bold green]Active[/bold green] Consent")
        console.print("  [2] Document [bold red]Withdrawn[/bold red] Consent")
        console.print("  [C] Cancel")

        act_choice = Prompt.ask("Choose action [1/2/C]", default="1").strip()
        if act_choice.lower() in ("c", "cancel"):
            console.print("[yellow]Consent recording cancelled.[/yellow]")
            return
        if act_choice == "2":
            status = "withdrawn"
            action_desc = "Withdraw Consent"
        else:
            status = "active"
            action_desc = "Grant Active Consent"

        scope_version = Prompt.ask("Scope Version (schema 1-64 chars)", default="2026.1").strip()
        if not scope_version:
            console.print("[bold red]Scope Version is required and cannot be empty.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return
        if len(scope_version) > 64:
            console.print("[bold red]Scope Version must not exceed 64 characters.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        # Explicit confirmation
        console.print(f"\n[bold]Confirmation Summary:[/bold]")
        console.print(f"• Child: {child_code} ({self.active_child_id})")
        console.print(f"• Purpose: clinical_assessment")
        console.print(f"• Scope Version: {scope_version}")
        console.print(f"• Action: {action_desc}")

        confirm = Prompt.ask("\nAre you sure you wish to record this consent status? (y/n)", default="y").strip().lower()
        if confirm not in ("y", "yes"):
            console.print("[yellow]Consent recording cancelled.[/yellow]")
            return

        # Target verification check before dispatch
        if not self.active_child_id:
            console.print("[bold red]Child context was cleared. Aborting mutation.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        try:
            new_consent = self.client.record_consent(
                self.active_child_id,
                "clinical_assessment",
                scope_version,
                status,
            )
            console.print(f"[bold green]✓ Consent recorded on server (Version {new_consent.get('version', 1)})[/bold green]")
            # Asynchronously refresh authoritative state
            try:
                self._resolve_consent_state(self.active_child_id)
            except LinguaLensAuthError:
                raise
            except LinguaLensPermissionError as exc:
                console.print(f"[bold yellow]⚠️ Consent recorded, but permission was denied to refresh history: {exc}[/bold yellow]")
            except Exception as exc:
                console.print(f"[bold yellow]⚠️ Consent recorded, but failed to refresh history: {exc}[/bold yellow]")

        except LinguaLensAuthError:
            raise
        except LinguaLensPermissionError as exc:
            console.print(f"[bold red]⛔ Permission Denied: {exc}[/bold red]")
            raise
        except LinguaLensConflictError as exc:
            console.print(f"[bold red]⚠️ Consent Conflict (409): {exc}[/bold red]")
            self._resolve_consent_state(self.active_child_id)
        except Exception as exc:
            console.print(f"[bold red]⚠️ Failed to record consent: {exc}[/bold red]")

        Prompt.ask("Press Enter to continue")

    def _children_menu(self) -> str:
        """Render children directory and handle selection / creation for Assessment V2."""
        while True:
            children = self.client.list_children()
            render_children_table(children)

            if self.active_child_id:
                child_code = self.active_child.get("display_code", self.active_child_id) if self.active_child else self.active_child_id
                status, rec = self._resolve_consent_state(self.active_child_id)
                if status == "active":
                    v = rec.get("version", 1) if rec else 1
                    status_fmt = f"[bold green]✓ Active (v{v})[/bold green]"
                elif status == "withdrawn":
                    v = rec.get("version", "") if rec else ""
                    v_str = f" (v{v})" if v else ""
                    status_fmt = f"[bold red]⛔ Withdrawn{v_str}[/bold red]"
                elif status == "no-record":
                    status_fmt = "[dim]⚪ No Record[/dim]"
                else:
                    status_fmt = f"[bold red]⚠️ Error loading consent[/bold red]"

                asmt_info = f" | Assessment: [bold magenta]{self.active_assessment_id}[/bold magenta]" if self.active_assessment_id else ""
                console.print(f"\n[bold]Selected Child:[/bold] [cyan]{child_code}[/cyan] ({self.active_child_id}) | Consent: {status_fmt}{asmt_info}")

            console.print("\n[bold cyan]Actions:[/bold cyan]")
            if children:
                console.print("  [1-N] Select Child Number to set as active")
            if self.active_child_id:
                console.print("  [C]   Record / Update [bold yellow]C[/bold yellow]onsent")
                console.print("  [A]   Create [bold magenta]A[/bold magenta]ssessment (V2)")
            console.print("  [N]   Create [bold green]N[/bold green]ew Child Profile")
            console.print("  [R]   [bold cyan]R[/bold cyan]efresh Directory & Consent")
            console.print("  [B]   [bold blue]B[/bold blue]ack")
            console.print("  [Q]   [bold red]Q[/bold red]uit")

            choice = Prompt.ask("\nChoose an option", default="b")
            if choice.lower() in ("q", "quit", "exit"):
                return "exit"
            if choice.lower() in ("b", "back"):
                return "back"
            if choice.lower() == "n":
                self._create_child_wizard()
                continue
            if choice.lower() == "r":
                continue
            if choice.lower() == "c" and self.active_child_id:
                self._record_consent_wizard()
                continue
            if choice.lower() == "a" and self.active_child_id:
                self._create_assessment_wizard()
                continue

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(children):
                    self._set_active_child(children[idx]["id"])
                    console.print(f"[bold green]✓ Active child set to: {children[idx].get('display_code', children[idx]['id'])}[/bold green]")
                    Prompt.ask("Press Enter to continue")
                    continue
            except ValueError:
                pass

            console.print("[red]Invalid selection.[/red]")
            Prompt.ask("Press Enter to continue")

    def _create_assessment_wizard(self) -> None:
        """Prompt for assessment creation, enforce active consent gate, and isolate assessment context."""
        if not self.active_child_id:
            console.print("[bold red]⚠️ Please select a child profile first.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        # Precheck active consent
        status, rec = self._resolve_consent_state(self.active_child_id)
        if status != "active" or not rec:
            console.print("[bold red]⚠️ Active clinical assessment consent is required before creating an assessment. Please record consent first.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        child_code = self.active_child.get("display_code", self.active_child_id) if self.active_child else self.active_child_id
        console.print(f"\n[bold magenta]➕ Start New Clinical Assessment (Assessment V2)[/bold magenta]")
        console.print(f"Child Profile: [cyan]{child_code}[/cyan] ({self.active_child_id})")

        console.print("\nAssessment Purpose:")
        console.print("  [1] initial (Default)")
        console.print("  [2] developmental_follow_up")
        console.print("  [3] post_intervention_follow_up")
        console.print("  [4] additional_evidence")
        purpose_choice = Prompt.ask("Choose purpose [1-4]", default="1").strip()
        purpose_map = {
            "1": "initial",
            "2": "developmental_follow_up",
            "3": "post_intervention_follow_up",
            "4": "additional_evidence",
        }
        if purpose_choice not in purpose_map:
            console.print("[bold red]⚠️ Invalid assessment purpose. Must be one of 1-4 (initial, developmental_follow_up, post_intervention_follow_up, additional_evidence).[/bold red]")
            Prompt.ask("Press Enter to continue")
            return
        purpose = purpose_map[purpose_choice]

        clinician_id = Prompt.ask("Assigned Clinician ID (leave blank for server default)", default="").strip()
        clean_clinician = clinician_id if clinician_id else None
        if clean_clinician and len(clean_clinician) > 128:
            console.print("[bold red]⚠️ Assigned Clinician ID must not exceed 128 characters.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        # Confirmation
        console.print("\n[bold]Confirmation Summary:[/bold]")
        console.print(f"• Child: {child_code} ({self.active_child_id})")
        console.print(f"• Purpose: {purpose}")
        console.print(f"• Assigned Clinician: {clean_clinician or '(Server default)'}")

        confirm = Prompt.ask("\nAre you sure you wish to start this assessment? (y/n)", default="y").strip().lower()
        if confirm not in ("y", "yes"):
            console.print("[yellow]Assessment creation cancelled.[/yellow]")
            Prompt.ask("Press Enter to continue")
            return

        # Re-check active child context
        if not self.active_child_id:
            console.print("[bold red]Child context changed or cleared. Aborting.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        try:
            new_asmt = self.client.create_assessment(
                self.active_child_id,
                purpose=purpose,
                assigned_clinician_id=clean_clinician,
            )
            self.active_assessment_id = new_asmt.get("id")
            self.active_assessment = new_asmt
            self.active_session_id = None
            console.print(f"[bold green]✓ Assessment created successfully: {self.active_assessment_id}[/bold green]")
            Prompt.ask("Press Enter to continue")
        except LinguaLensAuthError:
            raise
        except LinguaLensPermissionError as exc:
            console.print(f"[bold red]⛔ Permission Denied: {exc}[/bold red]")
            Prompt.ask("Press Enter to continue")
        except LinguaLensConflictError as exc:
            console.print(f"[bold red]⚠️ Assessment Conflict (409): {exc}[/bold red]")
            self.active_assessment_id = None
            self.active_assessment = None
            # Re-fetch authoritative consent state
            try:
                self._resolve_consent_state(self.active_child_id)
            except Exception:
                pass
            Prompt.ask("Press Enter to continue")
        except Exception as exc:
            console.print(f"[bold red]⚠️ Failed to create assessment: {exc}[/bold red]")
            Prompt.ask("Press Enter to continue")

    def _create_child_wizard(self) -> None:
        """Prompt for child intake parameters, validate client-side, and create profile."""
        console.print("\n[bold green]➕ Create Child Profile (Assessment V2)[/bold green]")
        display_code = Prompt.ask("Child Identifier / Display Code", default="C-0301").strip()
        birth_year_str = Prompt.ask("Birth Year (YYYY)", default="2021").strip()
        birth_month_str = Prompt.ask("Birth Month (1-12)", default="6").strip()
        lang = Prompt.ask("Primary Language (th/en)", default="th").strip()

        if not display_code or len(display_code) > 64:
            console.print("[bold red]Display Code must be between 1 and 64 characters.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        try:
            birth_year = int(birth_year_str)
            if not (1900 <= birth_year <= 2100):
                console.print("[bold red]Birth year must be between 1900 and 2100.[/bold red]")
                Prompt.ask("Press Enter to continue")
                return
        except ValueError:
            console.print("[bold red]Invalid birth year.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        try:
            birth_month = int(birth_month_str)
            if not (1 <= birth_month <= 12):
                console.print("[bold red]Birth month must be between 1 and 12.[/bold red]")
                Prompt.ask("Press Enter to continue")
                return
        except ValueError:
            console.print("[bold red]Invalid birth month.[/bold red]")
            Prompt.ask("Press Enter to continue")
            return

        lang_ctx = {"primary": lang or "th", "additional": []}
        try:
            new_child = self.client.create_child(display_code, birth_year, birth_month, lang_ctx)
            console.print(f"[bold green]✓ Child profile created successfully: {new_child['id']}[/bold green]")
            self._set_active_child(new_child["id"])
        except (LinguaLensAuthError, LinguaLensPermissionError):
            raise
        except Exception as exc:
            console.print(f"[bold red]⚠️ Failed to create child: {exc}[/bold red]")
        Prompt.ask("Press Enter to continue")

    # --- Step 2: Sessions Menu ---
    def _sessions_menu(self) -> str:
        sessions = self.client.list_sessions(self.active_case_id)
        render_sessions_table(self.active_case_id, sessions)

        console.print("\n[bold cyan]Actions:[/bold cyan]")
        if sessions:
            console.print("  [1-N] Select Session Number to open")
        console.print("  [N]   Start [bold green]N[/bold green]ew Therapy Session")
        console.print("  [B]   [bold blue]B[/bold blue]ack to Cases Directory")
        console.print("  [Q]   [bold red]Q[/bold red]uit")

        choice = Prompt.ask("\nChoose an option", default="1" if sessions else "n")
        if choice.lower() in ("q", "quit", "exit"):
            return "exit"
        if choice.lower() in ("b", "back"):
            return "back"
        if choice.lower() == "n":
            self._create_session_wizard()
            return "continue"

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                self.active_session_id = sessions[idx]["session_id"]
                return "continue"
        except ValueError:
            pass

        console.print("[red]Invalid selection.[/red]")
        Prompt.ask("Press Enter to continue")
        return "continue"

    def _create_session_wizard(self) -> None:
        from datetime import date
        today = date.today().isoformat()
        console.print("\n[bold green]➕ Start New Therapy Session[/bold green]")
        s_date = Prompt.ask("Session Date (YYYY-MM-DD)", default=today)
        notes = Prompt.ask("Session Goals / Notes", default="Naturalistic play and language sampling.")

        new_s = self.client.create_session(self.active_case_id, s_date, notes)
        console.print(f"[bold green]✓ Session started: {new_s['session_id']}[/bold green]")
        self.active_session_id = new_s["session_id"]
        Prompt.ask("Press Enter to open Session Workspace")

    # --- Step 3, 4, 5: Session Workspace Hub ---
    def _session_workspace_menu(self) -> str:
        self.active_transcript = self.client.get_session_transcript(self.active_session_id)
        has_transcript = bool(self.active_transcript and self.active_transcript.get("utterances"))
        is_attested = bool(self.active_transcript and self.active_transcript.get("attested"))

        console.print(f"\n[bold]Current Case:[/bold] [cyan]{self.active_case_id}[/cyan] | [bold]Session:[/bold] [cyan]{self.active_session_id}[/cyan]")
        tr_status = "[green]Ingested & Attested[/green]" if is_attested else ("[yellow]Ingested (Needs Review)[/yellow]" if has_transcript else "[red]Not Uploaded[/red]")
        console.print(f"[bold]Transcript Status:[/bold] {tr_status}")

        console.print("\n[bold cyan]Session Workspace Options (5-Step Workflow):[/bold cyan]")
        console.print("  [1] 📥 Ingest / Upload Transcript (.cha, txt, or manual text)")
        console.print("  [2] 🗣️  Human-in-the-Loop Transcript Review & Attestation")
        console.print("  [3] 📊 View Speech-Language Findings & Guideline Linkages")
        console.print("  [4] 📝 Generate / View Progress Report (Draft & Sign-Off)")
        console.print("  [5] 💾 Export Report & Findings to File (.md / .txt)")
        console.print("  [B] 🔙 Back to Sessions List")
        console.print("  [Q] ❌ Quit")

        choice = Prompt.ask("\nSelect Workflow Step", default="2" if has_transcript else "1")
        if choice.lower() in ("q", "quit", "exit"):
            return "exit"
        if choice.lower() in ("b", "back"):
            return "back"
        if choice == "1":
            self._ingest_transcript_flow()
        elif choice == "2":
            self._review_transcript_flow()
        elif choice == "3":
            self._view_findings_flow()
        elif choice == "4":
            self._report_flow()
        elif choice == "5":
            self._export_flow()

        return "continue"

    # --- Step 3 Subflow: Transcript Ingestion ---
    def _ingest_transcript_flow(self) -> None:
        if getattr(self, "current_mode", "legacy") == "v2" or self.active_child_id or self.active_assessment_id or not self.active_case_id or not self.active_session_id:
            console.print("[yellow]⚠️ Operation unavailable: Requires active legacy case and session context.[/yellow]")
            return

        console.print("\n[bold cyan]📥 Transcript Ingestion Mode[/bold cyan]")
        console.print("  [1] Load Sample Thai Play Dialogue (Demo)")
        console.print("  [2] Ingest from local .cha or .txt file")
        console.print("  [3] Paste Raw Dialogue Text")
        console.print("  [4] 🎙️ Ingest from Audio/Video File (.wav, .mp3, .m4a, .mp4) & Extract Acoustic Profile")

        sub = Prompt.ask("Choose Ingestion Source", default="1")
        if sub == "1":
            sample_text = (
                "INV: สวัสดีครับ วันนี้เรามาเล่นของเล่นด้วยกันนะ\n"
                "CHI: เล่น รถ\n"
                "INV: อยากได้รถคันไหนครับ มีสีแดงกับสีน้ำเงิน\n"
                "CHI: แดง รถ แดง ไป\n"
                "INV: รถสีแดงวิ่งเร็วมากเลย บรู๊น บรู๊น\n"
                "CHI: ไป หา แม่\n"
                "INV: เดี๋ยวเล่นเสร็จแล้วไปหาคุณแม่ด้วยกันนะครับ"
            )
            self.active_transcript = self.client.ingest_transcript_text(self.active_session_id, sample_text)
            console.print("[bold green]✓ Sample transcript ingested successfully with 7 utterances![/bold green]")
        elif sub == "2":
            file_path = Prompt.ask("Enter path to .cha or .txt file")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.active_transcript = self.client.ingest_transcript_text(self.active_session_id, content)
                console.print(f"[bold green]✓ Ingested from file: {file_path}[/bold green]")
            else:
                console.print(f"[bold red]File not found: {file_path}[/bold red]")
        elif sub == "3":
            console.print("[dim]Enter dialogue lines (Type 'EOF' on a new line when done):[/dim]")
            lines = []
            while True:
                line = input()
                if line.strip() == "EOF":
                    break
                lines.append(line)
            raw = "\n".join(lines)
            if raw.strip():
                self.active_transcript = self.client.ingest_transcript_text(self.active_session_id, raw)
                console.print("[bold green]✓ Transcript ingested successfully![/bold green]")
        elif sub == "4":
            audio_path = Prompt.ask("Enter path to audio/video file (.wav, .mp3, .m4a, .mp4)")
            if os.path.exists(audio_path):
                try:
                    console.print(f"[cyan]🔄 Processing audio file and extracting acoustic & speech features...[/cyan]")
                    self.active_transcript = self.client.ingest_audio_file(self.active_session_id, audio_path)
                    console.print(f"[bold green]✓ Audio processed successfully! Transcripts & Acoustic Profile extracted.[/bold green]")
                except Exception as exc:
                    console.print(f"[bold red]Failed to process audio: {exc}[/bold red]")
            else:
                console.print(f"[bold red]File not found: {audio_path}[/bold red]")

        Prompt.ask("Press Enter to continue")

    # --- Step 4 Subflow: Human-in-the-loop Review ---
    def _review_transcript_flow(self) -> None:
        if getattr(self, "current_mode", "legacy") == "v2" or self.active_child_id or self.active_assessment_id or not self.active_case_id or not self.active_session_id:
            console.print("[yellow]⚠️ Operation unavailable: Requires active legacy case and session context.[/yellow]")
            return

        if not self.active_transcript or not self.active_transcript.get("utterances"):
            console.print("[yellow]⚠️ No transcript available. Please ingest a transcript first (Step 1).[/yellow]")
            Prompt.ask("Press Enter to continue")
            return

        while True:
            console.clear()
            print_banner(api_online=self.client.check_health(), current_step="Transcript Review")
            utterances = self.active_transcript["utterances"]
            is_attested = self.active_transcript.get("attested", False)
            render_transcript_review_table(utterances, attested=is_attested)

            console.print("\n[bold cyan]Review Actions:[/bold cyan]")
            console.print("  [1-N] Select Utterance Number to Edit Text/Speaker")
            if not is_attested:
                console.print("  [S]   [bold green]S[/bold green]ign-off & Attest Transcript (Clinician Verification)")
            console.print("  [B]   [bold blue]B[/bold blue]ack to Workspace Hub")

            choice = Prompt.ask("\nSelect action", default="s" if not is_attested else "b")
            if choice.lower() in ("b", "back"):
                break
            if choice.lower() in ("s", "signoff", "attest") and not is_attested:
                therapist_name = Prompt.ask("Clinician / Therapist Name", default="Kru Aum (SLP)")
                self.active_transcript = self.client.attest_transcript(self.active_transcript["transcript_id"], therapist_name)
                console.print(f"[bold green]✓ Transcript successfully attested by {therapist_name}![/bold green]")
                Prompt.ask("Press Enter to continue")
                break

            try:
                u_idx = int(choice) - 1
                if 0 <= u_idx < len(utterances):
                    u = utterances[u_idx]
                    console.print(f"\n[bold]Editing Utterance #{u_idx + 1}[/bold]")
                    new_spk = Prompt.ask("Speaker (CHI/INV/MOT/FAT)", default=u.get("speaker", "CHI"))
                    new_text = Prompt.ask("Utterance Text", default=u.get("text", ""))
                    self.active_transcript = self.client.update_utterance(
                        self.active_transcript["transcript_id"],
                        u["id"],
                        new_text,
                        new_spk,
                    )
                    console.print("[green]✓ Utterance updated.[/green]")
                    Prompt.ask("Press Enter to refresh")
            except ValueError:
                pass

    # --- Step 5 Subflow: Findings ---
    def _view_findings_flow(self) -> None:
        if getattr(self, "current_mode", "legacy") == "v2" or self.active_child_id or self.active_assessment_id or not self.active_case_id or not self.active_session_id:
            console.print("[yellow]⚠️ Operation unavailable: Requires active legacy case and session context.[/yellow]")
            return

        findings = self.client.get_findings(self.active_session_id)
        console.clear()
        print_banner(api_online=self.client.check_health(), current_step="Clinical Findings")
        render_findings_view(findings)
        Prompt.ask("\nPress Enter to return to Session Workspace")

    # --- Step 5 Subflow: Reports ---
    def _report_flow(self) -> None:
        if getattr(self, "current_mode", "legacy") == "v2" or self.active_child_id or self.active_assessment_id or not self.active_case_id or not self.active_session_id:
            console.print("[yellow]⚠️ Operation unavailable: Requires active legacy case and session context.[/yellow]")
            return

        console.clear()
        print_banner(api_online=self.client.check_health(), current_step="Progress Report")

        # Check existing reports
        report_data = self.client.get_session_report(self.active_session_id)

        if not report_data:
            console.print("[yellow]No report exists yet for this session.[/yellow]")
            if Confirm.ask("Would you like to generate a Clinical Progress Report Draft now?", default=True):
                notes = Prompt.ask("Therapist focus / clinical observations", default="Focus on phrase expansion.")
                report_data = self.client.draft_report(self.active_session_id, notes)
                console.print("[bold green]✓ Progress report draft created![/bold green]")
            else:
                return

        render_report_view(report_data)

        if report_data.get("status") != "Signed Off":
            if Confirm.ask("\nWould you like to complete Digital Clinician Sign-off?", default=True):
                signer = Prompt.ask("Therapist Name & Title", default="Kru Aum (SLP)")
                report_data = self.client.sign_off_report(report_data["report_id"], signer)
                console.print(f"[bold green]✓ Report signed off! SHA-256 Hash: {report_data.get('sha256_hash')}[/bold green]")
                render_report_view(report_data)

        Prompt.ask("\nPress Enter to return to Session Workspace")

    # --- Step 5 Export Subflow ---
    def _export_flow(self) -> None:
        if getattr(self, "current_mode", "legacy") == "v2" or self.active_child_id or self.active_assessment_id or not self.active_case_id or not self.active_session_id:
            console.print("[yellow]⚠️ Operation unavailable: Requires active legacy case and session context.[/yellow]")
            return

        findings = self.client.get_findings(self.active_session_id)
        report_data = self.client.get_session_report(self.active_session_id)

        out_path = f"reports/export_{self.active_session_id}.md"
        os.makedirs("reports", exist_ok=True)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# LinguaLens Clinical Progress Report\n\n")
            f.write(f"- **Case ID:** {self.active_case_id}\n")
            f.write(f"- **Session ID:** {self.active_session_id}\n")
            f.write(f"- **Exported At:** 2026-08-16\n")
            f.write(f"- **Clinical Safety Note:** Research/educational decision support prototype; non-diagnostic.\n\n")

            f.write(f"## 1. Speech-Language Metrics\n\n")
            metrics = findings.get("metrics", {})
            for k, v in metrics.items():
                f.write(f"- **{k}:** {v}\n")

            f.write(f"\n## 2. Clinical Guideline Mappings\n\n")
            for g in findings.get("guideline_links", []):
                f.write(f"- **{g.get('construct')}:** {g.get('status')} ({g.get('description')})\n")

            if report_data:
                f.write(f"\n## 3. Therapist Clinical Narrative\n\n")
                f.write(f"{report_data.get('narrative', '')}\n\n")
                f.write(f"### Recommendations & Goals\n\n")
                f.write(f"{report_data.get('recommendations', '')}\n\n")
                f.write(f"- **Sign-Off Status:** {report_data.get('status')}\n")
                f.write(f"- **Signed By:** {report_data.get('signed_by')}\n")
                f.write(f"- **Integrity Hash:** `{report_data.get('sha256_hash', '-')}`\n")

        console.print(f"[bold green]✓ Full Session & Report exported to file: [cyan]{out_path}[/cyan][/bold green]")
        Prompt.ask("Press Enter to return")
