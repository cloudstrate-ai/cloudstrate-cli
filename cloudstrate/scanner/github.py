"""
GitHub Scanner wrapper for Cloudstrate CLI.

Wraps the existing github_scanner module for use with the CLI.
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional


class GitHubScanner:
    """Wrapper for GitHub organization scanning.

    Provides a unified interface for the CLI to scan GitHub infrastructure.
    """

    def __init__(
        self,
        organization: str,
        include_workflows: bool = True,
        include_oidc: bool = True,
        token_env: str = "GITHUB_TOKEN",
    ):
        """Initialize GitHub scanner.

        Args:
            organization: GitHub organization name
            include_workflows: Include GitHub Actions workflows in scan
            include_oidc: Include OIDC configuration
            token_env: Environment variable containing GitHub token
        """
        self.organization = organization
        self.include_workflows = include_workflows
        self.include_oidc = include_oidc
        self.token_env = token_env

    def scan(self) -> dict[str, Any]:
        """Run GitHub organization scan.

        Returns:
            Dictionary containing scan results with:
            - organization: Organization metadata
            - repositories: List of repositories
            - workflows: GitHub Actions workflows (if enabled)
            - oidc: OIDC configurations (if enabled)
        """
        import os

        token = os.environ.get(self.token_env)
        if not token:
            raise ValueError(
                f"GitHub token not found in environment variable: {self.token_env}"
            )

        try:
            # Try to import existing scanner
            foundation_path = Path(__file__).parent.parent.parent / "foundation"
            sys.path.insert(0, str(foundation_path))

            from github_scanner.scanner import GitHubOrgScanner

            scanner = GitHubOrgScanner(
                organization=self.organization,
                token=token,
            )

            result = scanner.scan()

            # Filter based on options
            if not self.include_workflows:
                result.pop("workflows", None)

            if not self.include_oidc:
                result.pop("oidc_configs", None)

            return result

        except ImportError:
            # Fallback to basic implementation using PyGithub
            return self._scan_basic(token)

    def _scan_basic(self, token: str) -> dict[str, Any]:
        """Basic GitHub scan using PyGithub.

        Fallback if the existing scanner is not available.
        """
        try:
            from github import Github
        except ImportError:
            raise ImportError("PyGithub is required. Install with: pip install PyGithub")

        g = Github(token)
        org = g.get_organization(self.organization)

        result = {
            "organization": {
                "name": org.name,
                "login": org.login,
                "description": org.description,
                "url": org.html_url,
            },
            "repositories": [],
        }

        for repo in org.get_repos():
            repo_data = {
                "name": repo.name,
                "full_name": repo.full_name,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "url": repo.html_url,
            }

            if self.include_workflows:
                try:
                    workflows = []
                    for workflow in repo.get_workflows():
                        workflows.append({
                            "name": workflow.name,
                            "path": workflow.path,
                            "state": workflow.state,
                        })
                    repo_data["workflows"] = workflows
                except Exception:
                    repo_data["workflows"] = []

            result["repositories"].append(repo_data)

        return result
