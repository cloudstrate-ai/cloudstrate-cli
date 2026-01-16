"""
GitHub permissions setup and validation.

Validates GitHub token and required permissions for scanning.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GitHubPermissionCheck:
    """Result of a permission check."""
    scope: str
    allowed: bool
    error: Optional[str] = None


@dataclass
class GitHubStatus:
    """Status of GitHub setup."""
    authenticated: bool
    username: Optional[str] = None
    token_type: Optional[str] = None  # classic, fine-grained
    organization: Optional[str] = None
    org_accessible: bool = False
    scopes: list[str] = field(default_factory=list)
    permission_checks: list[GitHubPermissionCheck] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def all_permissions_valid(self) -> bool:
        """Check if all permissions are valid."""
        return all(p.allowed for p in self.permission_checks)


class GitHubSetup:
    """GitHub permissions setup and validation."""

    # Required scopes for organization scanning
    REQUIRED_SCOPES = [
        "repo",           # Repository access
        "read:org",       # Organization membership
        "admin:org",      # Organization admin (for OIDC configs) - optional
        "workflow",       # GitHub Actions workflows
    ]

    def __init__(
        self,
        token: Optional[str] = None,
        token_env: str = "GITHUB_TOKEN",
        organization: Optional[str] = None,
    ):
        """Initialize GitHub setup.

        Args:
            token: GitHub token (or None to read from env)
            token_env: Environment variable name for token
            organization: GitHub organization to validate
        """
        self.token = token or os.environ.get(token_env)
        self.token_env = token_env
        self.organization = organization

    def check_token(self) -> GitHubStatus:
        """Check GitHub token and return basic status.

        Returns:
            GitHubStatus with authentication details
        """
        if not self.token:
            return GitHubStatus(
                authenticated=False,
                error=f"GitHub token not found. Set {self.token_env} environment variable.",
            )

        try:
            from github import Github, GithubException

            g = Github(self.token)

            # Get authenticated user
            user = g.get_user()

            # Determine token type based on format
            if self.token.startswith("ghp_"):
                token_type = "classic"
            elif self.token.startswith("github_pat_"):
                token_type = "fine-grained"
            elif self.token.startswith("gho_"):
                token_type = "oauth"
            else:
                token_type = "unknown"

            # Get scopes from rate limit response (classic tokens)
            scopes = []
            try:
                # This is a hack to get scopes - make a request and check headers
                rate_limit = g.get_rate_limit()
                # Scopes are in the response headers but not easily accessible
                # For now, we'll test permissions directly
            except Exception:
                pass

            status = GitHubStatus(
                authenticated=True,
                username=user.login,
                token_type=token_type,
                scopes=scopes,
            )

            # Check organization access if specified
            if self.organization:
                status.organization = self.organization
                try:
                    org = g.get_organization(self.organization)
                    # Try to access org details
                    _ = org.login
                    status.org_accessible = True
                except GithubException as e:
                    if e.status == 404:
                        status.error = f"Organization '{self.organization}' not found"
                    elif e.status == 403:
                        status.error = f"Access denied to organization '{self.organization}'"
                    status.org_accessible = False

            return status

        except Exception as e:
            return GitHubStatus(
                authenticated=False,
                error=str(e),
            )

    def check_permissions(self) -> GitHubStatus:
        """Check required permissions for scanning.

        Returns:
            GitHubStatus with permission check results
        """
        status = self.check_token()
        if not status.authenticated:
            return status

        try:
            from github import Github, GithubException

            g = Github(self.token)
            checks = []

            # Test repo access
            try:
                user = g.get_user()
                repos = list(user.get_repos()[:1])
                checks.append(GitHubPermissionCheck(
                    scope="repo",
                    allowed=True,
                ))
            except GithubException as e:
                checks.append(GitHubPermissionCheck(
                    scope="repo",
                    allowed=False,
                    error=str(e),
                ))

            # Test org access
            if self.organization:
                try:
                    org = g.get_organization(self.organization)
                    # Try to list repos
                    repos = list(org.get_repos()[:1])
                    checks.append(GitHubPermissionCheck(
                        scope="read:org",
                        allowed=True,
                    ))
                except GithubException as e:
                    checks.append(GitHubPermissionCheck(
                        scope="read:org",
                        allowed=False,
                        error=str(e),
                    ))

                # Test workflow access
                try:
                    repos = org.get_repos()
                    for repo in repos:
                        try:
                            workflows = list(repo.get_workflows()[:1])
                            checks.append(GitHubPermissionCheck(
                                scope="workflow",
                                allowed=True,
                            ))
                            break
                        except Exception:
                            continue
                    else:
                        checks.append(GitHubPermissionCheck(
                            scope="workflow",
                            allowed=True,  # No workflows to test
                        ))
                except GithubException as e:
                    checks.append(GitHubPermissionCheck(
                        scope="workflow",
                        allowed=False,
                        error=str(e),
                    ))

            status.permission_checks = checks
            return status

        except Exception as e:
            status.error = str(e)
            return status

    def get_required_scopes_help(self) -> str:
        """Get help text for required GitHub token scopes.

        Returns:
            Help text explaining required permissions
        """
        return """
Required GitHub Token Scopes:

For Classic Tokens (ghp_...):
  - repo: Full control of private repositories
  - read:org: Read org and team membership
  - workflow: Update GitHub Action workflows (optional)
  - admin:org: Full control of orgs (optional, for OIDC configs)

For Fine-Grained Tokens (github_pat_...):
  Repository permissions:
    - Contents: Read
    - Metadata: Read
    - Actions: Read (for workflows)

  Organization permissions:
    - Members: Read
    - Administration: Read (for OIDC configs)

Create a token at: https://github.com/settings/tokens
"""
