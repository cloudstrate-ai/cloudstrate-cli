"""Tests for the setup module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from cloudstrate.setup.neo4j import Neo4jSetup, Neo4jStatus
from cloudstrate.setup.aws import AWSSetup, AWSStatus, AWSPermissionCheck
from cloudstrate.setup.github import GitHubSetup, GitHubStatus, GitHubPermissionCheck


class TestNeo4jSetup:
    """Tests for Neo4jSetup class."""

    def test_init_defaults(self):
        """Test default initialization."""
        setup = Neo4jSetup(password="test123")
        assert setup.uri == "bolt://localhost:7687"
        assert setup.user == "neo4j"
        assert setup.password == "test123"
        assert setup.database == "neo4j"

    def test_init_custom_values(self):
        """Test custom initialization."""
        setup = Neo4jSetup(
            uri="bolt://custom:7687",
            user="admin",
            password="secret",
            database="mydb",
        )
        assert setup.uri == "bolt://custom:7687"
        assert setup.user == "admin"
        assert setup.password == "secret"
        assert setup.database == "mydb"

    def test_check_neo4j_installed_found(self):
        """Test checking Neo4j installation when found."""
        setup = Neo4jSetup(password="test")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="neo4j 5.0.0")
            installed, version = setup.check_neo4j_installed()
            assert installed is True
            assert "5.0.0" in version

    def test_check_neo4j_installed_not_found(self):
        """Test checking Neo4j installation when not found."""
        setup = Neo4jSetup(password="test")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            installed, msg = setup.check_neo4j_installed()
            assert installed is False
            assert "not found" in msg.lower()

    def test_check_connection_no_password(self):
        """Test connection check without password."""
        setup = Neo4jSetup(password=None)
        status = setup.check_connection()
        assert status.connected is False
        assert "password" in status.error.lower()

    def test_check_connection_success(self):
        """Test successful connection check."""
        setup = Neo4jSetup(password="test")
        with patch("neo4j.GraphDatabase") as mock_gdb:
            mock_driver = Mock()
            mock_session = Mock()
            mock_gdb.driver.return_value = mock_driver
            mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_driver.session.return_value.__exit__ = Mock(return_value=None)

            # Mock version query
            mock_result1 = Mock()
            mock_result1.single.return_value = {"version": "5.0.0"}

            # Mock node count query
            mock_result2 = Mock()
            mock_result2.single.return_value = {"count": 100}

            mock_session.run.side_effect = [mock_result1, mock_result2]

            status = setup.check_connection()
            assert status.connected is True
            assert status.version == "5.0.0"
            assert status.node_count == 100

    def test_check_connection_auth_error(self):
        """Test connection check with auth error."""
        setup = Neo4jSetup(password="wrong")
        with patch("neo4j.GraphDatabase") as mock_gdb:
            from neo4j.exceptions import AuthError
            mock_gdb.driver.side_effect = AuthError("Bad credentials")

            status = setup.check_connection()
            assert status.connected is False
            assert "auth" in status.error.lower()

    def test_create_indexes_no_password(self):
        """Test index creation without password."""
        setup = Neo4jSetup(password=None)
        status = setup.create_indexes()
        assert status.connected is False

    def test_create_indexes_success(self):
        """Test successful index creation."""
        setup = Neo4jSetup(password="test")
        with patch("neo4j.GraphDatabase") as mock_gdb:
            mock_driver = Mock()
            mock_session = Mock()
            mock_gdb.driver.return_value = mock_driver
            mock_driver.session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_driver.session.return_value.__exit__ = Mock(return_value=None)
            mock_session.run.return_value = None

            status = setup.create_indexes()
            assert status.connected is True
            assert status.indexes_created > 0

    def test_clear_database_no_confirm(self):
        """Test database clear without confirmation."""
        setup = Neo4jSetup(password="test")
        result = setup.clear_database(confirm=False)
        assert result is False

    def test_get_schema_info_no_password(self):
        """Test schema info without password."""
        setup = Neo4jSetup(password=None)
        info = setup.get_schema_info()
        assert "error" in info


class TestAWSSetup:
    """Tests for AWSSetup class."""

    def test_init_defaults(self):
        """Test default initialization."""
        setup = AWSSetup()
        assert setup.profile is None
        assert setup.region == "us-east-1"

    def test_init_with_profile(self):
        """Test initialization with profile."""
        setup = AWSSetup(profile="my-profile", region="us-west-2")
        assert setup.profile == "my-profile"
        assert setup.region == "us-west-2"

    def test_check_credentials_success(self):
        """Test successful credentials check."""
        setup = AWSSetup(profile="test")
        with patch("boto3.Session") as mock_session:
            mock_sess = Mock()
            mock_session.return_value = mock_sess

            # STS client
            mock_sts = Mock()
            mock_sess.client.return_value = mock_sts
            mock_sts.get_caller_identity.return_value = {
                "Account": "123456789012",
                "Arn": "arn:aws:iam::123456789012:user/test",
            }

            # IAM client for alias
            mock_iam = Mock()
            mock_sess.client.side_effect = [mock_sts, mock_iam]
            mock_iam.list_account_aliases.return_value = {"AccountAliases": ["test-account"]}

            status = setup.check_credentials()
            assert status.authenticated is True
            assert status.account_id == "123456789012"

    def test_check_credentials_failure(self):
        """Test credentials check failure."""
        setup = AWSSetup()
        with patch("boto3.Session") as mock_session:
            mock_session.side_effect = Exception("No credentials")

            status = setup.check_credentials()
            assert status.authenticated is False
            assert "credentials" in status.error.lower()

    def test_check_permissions(self):
        """Test permissions check."""
        setup = AWSSetup()
        with patch.object(setup, "check_credentials") as mock_creds:
            mock_creds.return_value = AWSStatus(
                authenticated=True,
                account_id="123456789012",
            )
            with patch.object(setup, "_check_permission") as mock_check:
                mock_check.return_value = AWSPermissionCheck(
                    service="organizations",
                    action="DescribeOrganization",
                    allowed=True,
                )
                with patch.object(setup, "_get_session"):
                    status = setup.check_permissions()
                    assert status.authenticated is True
                    assert len(status.permission_checks) > 0

    def test_get_required_policy(self):
        """Test generating required IAM policy."""
        setup = AWSSetup()
        policy = setup.get_required_policy()
        assert "Version" in policy
        assert "Statement" in policy
        assert "organizations" in policy.lower()
        assert "iam" in policy.lower()
        assert "ec2" in policy.lower()

    def test_aws_status_failed_permissions(self):
        """Test AWSStatus failed_permissions property."""
        status = AWSStatus(
            authenticated=True,
            permission_checks=[
                AWSPermissionCheck(service="iam", action="ListRoles", allowed=True),
                AWSPermissionCheck(service="organizations", action="ListAccounts", allowed=False, error="Access denied"),
            ],
        )
        failed = status.failed_permissions
        assert len(failed) == 1
        assert failed[0].service == "organizations"

    def test_aws_status_all_permissions_valid(self):
        """Test AWSStatus all_permissions_valid property."""
        status = AWSStatus(
            authenticated=True,
            permission_checks=[
                AWSPermissionCheck(service="iam", action="ListRoles", allowed=True),
                AWSPermissionCheck(service="ec2", action="DescribeVpcs", allowed=True),
            ],
        )
        assert status.all_permissions_valid is True


class TestGitHubSetup:
    """Tests for GitHubSetup class."""

    def test_init_defaults(self):
        """Test default initialization."""
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):
            setup = GitHubSetup()
            assert setup.token == "test-token"
            assert setup.organization is None

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        setup = GitHubSetup(token="my-token", organization="my-org")
        assert setup.token == "my-token"
        assert setup.organization == "my-org"

    def test_check_token_missing(self):
        """Test token check with missing token."""
        with patch.dict("os.environ", {}, clear=True):
            setup = GitHubSetup(token=None)
            status = setup.check_token()
            assert status.authenticated is False
            assert "token" in status.error.lower()

    def test_check_token_classic(self):
        """Test token check with classic token."""
        setup = GitHubSetup(token="ghp_test123")
        with patch("github.Github") as mock_gh:
            mock_g = Mock()
            mock_gh.return_value = mock_g
            mock_user = Mock()
            mock_user.login = "testuser"
            mock_g.get_user.return_value = mock_user
            mock_g.get_rate_limit.return_value = Mock()

            status = setup.check_token()
            assert status.authenticated is True
            assert status.username == "testuser"
            assert status.token_type == "classic"

    def test_check_token_fine_grained(self):
        """Test token check with fine-grained token."""
        setup = GitHubSetup(token="github_pat_test123")
        with patch("github.Github") as mock_gh:
            mock_g = Mock()
            mock_gh.return_value = mock_g
            mock_user = Mock()
            mock_user.login = "testuser"
            mock_g.get_user.return_value = mock_user
            mock_g.get_rate_limit.return_value = Mock()

            status = setup.check_token()
            assert status.token_type == "fine-grained"

    def test_check_token_oauth(self):
        """Test token check with OAuth token."""
        setup = GitHubSetup(token="gho_test123")
        with patch("github.Github") as mock_gh:
            mock_g = Mock()
            mock_gh.return_value = mock_g
            mock_user = Mock()
            mock_user.login = "testuser"
            mock_g.get_user.return_value = mock_user
            mock_g.get_rate_limit.return_value = Mock()

            status = setup.check_token()
            assert status.token_type == "oauth"

    def test_check_token_org_accessible(self):
        """Test token check with accessible organization."""
        setup = GitHubSetup(token="ghp_test", organization="test-org")
        with patch("github.Github") as mock_gh:
            mock_g = Mock()
            mock_gh.return_value = mock_g
            mock_user = Mock()
            mock_user.login = "testuser"
            mock_g.get_user.return_value = mock_user
            mock_g.get_rate_limit.return_value = Mock()

            mock_org = Mock()
            mock_org.login = "test-org"
            mock_g.get_organization.return_value = mock_org

            status = setup.check_token()
            assert status.org_accessible is True
            assert status.organization == "test-org"

    def test_check_token_org_not_found(self):
        """Test token check with non-existent organization."""
        setup = GitHubSetup(token="ghp_test", organization="nonexistent")
        with patch("github.Github") as mock_gh:
            from github import GithubException
            mock_g = Mock()
            mock_gh.return_value = mock_g
            mock_user = Mock()
            mock_user.login = "testuser"
            mock_g.get_user.return_value = mock_user
            mock_g.get_rate_limit.return_value = Mock()

            mock_exc = GithubException(404, {"message": "Not Found"}, None)
            mock_g.get_organization.side_effect = mock_exc

            status = setup.check_token()
            assert status.org_accessible is False
            assert "not found" in status.error.lower()

    def test_check_permissions(self):
        """Test permissions check."""
        setup = GitHubSetup(token="ghp_test", organization="test-org")
        with patch.object(setup, "check_token") as mock_token:
            mock_token.return_value = GitHubStatus(
                authenticated=True,
                username="testuser",
            )
            with patch("github.Github") as mock_gh:
                mock_g = Mock()
                mock_gh.return_value = mock_g
                mock_user = Mock()
                mock_g.get_user.return_value = mock_user
                mock_user.get_repos.return_value = [Mock()]

                mock_org = Mock()
                mock_g.get_organization.return_value = mock_org
                mock_org.get_repos.return_value = [Mock(get_workflows=Mock(return_value=[]))]

                status = setup.check_permissions()
                assert status.authenticated is True
                assert len(status.permission_checks) > 0

    def test_get_required_scopes_help(self):
        """Test getting required scopes help text."""
        setup = GitHubSetup(token="test")
        help_text = setup.get_required_scopes_help()
        assert "repo" in help_text
        assert "read:org" in help_text
        assert "workflow" in help_text
        assert "github.com/settings/tokens" in help_text

    def test_github_status_all_permissions_valid(self):
        """Test GitHubStatus all_permissions_valid property."""
        status = GitHubStatus(
            authenticated=True,
            permission_checks=[
                GitHubPermissionCheck(scope="repo", allowed=True),
                GitHubPermissionCheck(scope="read:org", allowed=True),
            ],
        )
        assert status.all_permissions_valid is True

        status.permission_checks.append(
            GitHubPermissionCheck(scope="admin:org", allowed=False, error="Denied")
        )
        assert status.all_permissions_valid is False


class TestSetupCLI:
    """Tests for setup CLI commands."""

    def test_setup_group_exists(self):
        """Test that setup command group exists."""
        from cloudstrate.cli.setup import setup
        assert setup is not None
        assert setup.name == "setup"

    def test_setup_init_command_exists(self):
        """Test that init subcommand exists."""
        from cloudstrate.cli.setup import setup
        commands = [cmd for cmd in setup.commands.keys()]
        assert "init" in commands

    def test_setup_neo4j_command_exists(self):
        """Test that neo4j subcommand exists."""
        from cloudstrate.cli.setup import setup
        commands = [cmd for cmd in setup.commands.keys()]
        assert "neo4j" in commands

    def test_setup_aws_command_exists(self):
        """Test that aws subcommand exists."""
        from cloudstrate.cli.setup import setup
        commands = [cmd for cmd in setup.commands.keys()]
        assert "aws" in commands

    def test_setup_github_command_exists(self):
        """Test that github subcommand exists."""
        from cloudstrate.cli.setup import setup
        commands = [cmd for cmd in setup.commands.keys()]
        assert "github" in commands

    def test_setup_check_command_exists(self):
        """Test that check subcommand exists."""
        from cloudstrate.cli.setup import setup
        commands = [cmd for cmd in setup.commands.keys()]
        assert "check" in commands

    def test_setup_aws_show_policy(self):
        """Test aws --show-policy option."""
        from cloudstrate.cli.setup import aws
        runner = CliRunner()
        result = runner.invoke(aws, ["--show-policy"])
        assert result.exit_code == 0
        assert "IAM Policy" in result.output

    def test_setup_github_show_scopes(self):
        """Test github --show-scopes option."""
        from cloudstrate.cli.setup import github
        runner = CliRunner()
        result = runner.invoke(github, ["--show-scopes"])
        assert result.exit_code == 0
        assert "repo" in result.output


class TestDockerNeo4j:
    """Tests for Docker Neo4j startup."""

    def test_start_neo4j_docker_no_docker(self):
        """Test Docker startup when Docker is not available."""
        from cloudstrate.cli.setup import _start_neo4j_docker
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            result = _start_neo4j_docker("password")
            assert result is False

    def test_start_neo4j_docker_existing_container(self):
        """Test Docker startup with existing container."""
        from cloudstrate.cli.setup import _start_neo4j_docker
        with patch("subprocess.run") as mock_run:
            # First call: docker --version
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Docker version 20.10"),
                Mock(returncode=0, stdout="cloudstrate-neo4j"),  # container exists
                Mock(returncode=0),  # docker start
            ]
            result = _start_neo4j_docker("password")
            assert result is True

    def test_start_neo4j_docker_new_container(self):
        """Test Docker startup with new container."""
        from cloudstrate.cli.setup import _start_neo4j_docker
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout="Docker version 20.10"),
                Mock(returncode=0, stdout=""),  # no container
                Mock(returncode=0),  # docker run
            ]
            result = _start_neo4j_docker("password")
            assert result is True

    def test_start_neo4j_docker_exception(self):
        """Test Docker startup with exception."""
        from cloudstrate.cli.setup import _start_neo4j_docker
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Docker error")
            result = _start_neo4j_docker("password")
            assert result is False
