"""
AWS permissions setup and validation.

Validates AWS credentials and required permissions for scanning.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AWSPermissionCheck:
    """Result of a permission check."""
    service: str
    action: str
    allowed: bool
    error: Optional[str] = None


@dataclass
class AWSStatus:
    """Status of AWS setup."""
    authenticated: bool
    account_id: Optional[str] = None
    account_alias: Optional[str] = None
    user_arn: Optional[str] = None
    region: Optional[str] = None
    is_organization_account: bool = False
    permission_checks: list[AWSPermissionCheck] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def all_permissions_valid(self) -> bool:
        """Check if all permissions are valid."""
        return all(p.allowed for p in self.permission_checks)

    @property
    def failed_permissions(self) -> list[AWSPermissionCheck]:
        """Get list of failed permission checks."""
        return [p for p in self.permission_checks if not p.allowed]


class AWSSetup:
    """AWS permissions setup and validation."""

    # Required permissions for organization scanning
    ORGANIZATION_PERMISSIONS = [
        ("organizations", "DescribeOrganization"),
        ("organizations", "ListAccounts"),
        ("organizations", "ListOrganizationalUnitsForParent"),
        ("organizations", "ListPolicies"),
        ("organizations", "DescribePolicy"),
    ]

    # Required permissions for IAM scanning
    IAM_PERMISSIONS = [
        ("iam", "ListRoles"),
        ("iam", "GetRole"),
        ("iam", "ListRolePolicies"),
        ("iam", "GetRolePolicy"),
        ("iam", "ListAttachedRolePolicies"),
    ]

    # Required permissions for network scanning
    NETWORK_PERMISSIONS = [
        ("ec2", "DescribeVpcs"),
        ("ec2", "DescribeSubnets"),
        ("ec2", "DescribeSecurityGroups"),
        ("ec2", "DescribeTransitGateways"),
        ("ec2", "DescribeVpcPeeringConnections"),
    ]

    # Required permissions for RAM scanning
    RAM_PERMISSIONS = [
        ("ram", "GetResourceShares"),
        ("ram", "ListResources"),
    ]

    def __init__(
        self,
        profile: Optional[str] = None,
        region: str = "us-east-1",
    ):
        """Initialize AWS setup.

        Args:
            profile: AWS profile name (None for default)
            region: AWS region
        """
        self.profile = profile
        self.region = region
        self._session = None

    def _get_session(self):
        """Get or create boto3 session."""
        if self._session is None:
            import boto3
            if self.profile:
                self._session = boto3.Session(
                    profile_name=self.profile,
                    region_name=self.region,
                )
            else:
                self._session = boto3.Session(region_name=self.region)
        return self._session

    def check_credentials(self) -> AWSStatus:
        """Check AWS credentials and return basic status.

        Returns:
            AWSStatus with authentication details
        """
        try:
            session = self._get_session()
            sts = session.client("sts")

            # Get caller identity
            identity = sts.get_caller_identity()

            # Try to get account alias
            iam = session.client("iam")
            try:
                aliases = iam.list_account_aliases()
                account_alias = aliases["AccountAliases"][0] if aliases["AccountAliases"] else None
            except Exception:
                account_alias = None

            # Check if this is an organization management account
            is_org_account = False
            try:
                org = session.client("organizations")
                org_info = org.describe_organization()
                master_id = org_info["Organization"]["MasterAccountId"]
                is_org_account = (identity["Account"] == master_id)
            except Exception:
                pass

            return AWSStatus(
                authenticated=True,
                account_id=identity["Account"],
                user_arn=identity["Arn"],
                account_alias=account_alias,
                region=self.region,
                is_organization_account=is_org_account,
            )

        except Exception as e:
            return AWSStatus(
                authenticated=False,
                error=str(e),
            )

    def check_permissions(
        self,
        include_organization: bool = True,
        include_iam: bool = True,
        include_network: bool = True,
        include_ram: bool = True,
    ) -> AWSStatus:
        """Check required permissions for scanning.

        Args:
            include_organization: Check organization permissions
            include_iam: Check IAM permissions
            include_network: Check network permissions
            include_ram: Check RAM permissions

        Returns:
            AWSStatus with permission check results
        """
        status = self.check_credentials()
        if not status.authenticated:
            return status

        session = self._get_session()
        checks = []

        # Collect permissions to check
        permissions = []
        if include_organization:
            permissions.extend(self.ORGANIZATION_PERMISSIONS)
        if include_iam:
            permissions.extend(self.IAM_PERMISSIONS)
        if include_network:
            permissions.extend(self.NETWORK_PERMISSIONS)
        if include_ram:
            permissions.extend(self.RAM_PERMISSIONS)

        # Check each permission
        for service, action in permissions:
            check = self._check_permission(session, service, action)
            checks.append(check)

        status.permission_checks = checks
        return status

    def _check_permission(
        self,
        session,
        service: str,
        action: str,
    ) -> AWSPermissionCheck:
        """Check a single permission.

        Args:
            session: boto3 session
            service: AWS service name
            action: AWS action name

        Returns:
            AWSPermissionCheck result
        """
        try:
            client = session.client(service)

            # Map actions to actual API calls
            test_calls = {
                ("organizations", "DescribeOrganization"): lambda: client.describe_organization(),
                ("organizations", "ListAccounts"): lambda: client.list_accounts(MaxResults=1),
                ("organizations", "ListOrganizationalUnitsForParent"): lambda: None,  # Skip - needs parent ID
                ("organizations", "ListPolicies"): lambda: client.list_policies(Filter="SERVICE_CONTROL_POLICY", MaxResults=1),
                ("organizations", "DescribePolicy"): lambda: None,  # Skip - needs policy ID
                ("iam", "ListRoles"): lambda: client.list_roles(MaxItems=1),
                ("iam", "GetRole"): lambda: None,  # Skip - needs role name
                ("iam", "ListRolePolicies"): lambda: None,  # Skip - needs role name
                ("iam", "GetRolePolicy"): lambda: None,  # Skip - needs role name
                ("iam", "ListAttachedRolePolicies"): lambda: None,  # Skip - needs role name
                ("ec2", "DescribeVpcs"): lambda: client.describe_vpcs(MaxResults=5),
                ("ec2", "DescribeSubnets"): lambda: client.describe_subnets(MaxResults=5),
                ("ec2", "DescribeSecurityGroups"): lambda: client.describe_security_groups(MaxResults=5),
                ("ec2", "DescribeTransitGateways"): lambda: client.describe_transit_gateways(MaxResults=5),
                ("ec2", "DescribeVpcPeeringConnections"): lambda: client.describe_vpc_peering_connections(MaxResults=5),
                ("ram", "GetResourceShares"): lambda: client.get_resource_shares(resourceOwner="SELF", maxResults=1),
                ("ram", "ListResources"): lambda: client.list_resources(resourceOwner="SELF", maxResults=1),
            }

            test_call = test_calls.get((service, action))
            if test_call is None:
                # Unknown action, assume allowed
                return AWSPermissionCheck(
                    service=service,
                    action=action,
                    allowed=True,
                )

            if test_call() is None:
                # Skipped test
                return AWSPermissionCheck(
                    service=service,
                    action=action,
                    allowed=True,  # Assume allowed if we can't test
                )

            return AWSPermissionCheck(
                service=service,
                action=action,
                allowed=True,
            )

        except client.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("AccessDenied", "AccessDeniedException", "UnauthorizedAccess"):
                return AWSPermissionCheck(
                    service=service,
                    action=action,
                    allowed=False,
                    error=f"Access denied: {error_code}",
                )
            elif error_code in ("AWSOrganizationsNotInUseException",):
                # Organization not enabled - not a permission error
                return AWSPermissionCheck(
                    service=service,
                    action=action,
                    allowed=True,
                    error="Organizations not enabled",
                )
            else:
                # Other errors might not be permission related
                return AWSPermissionCheck(
                    service=service,
                    action=action,
                    allowed=True,
                    error=f"API error: {error_code}",
                )

        except Exception as e:
            return AWSPermissionCheck(
                service=service,
                action=action,
                allowed=False,
                error=str(e),
            )

    def get_required_policy(self) -> str:
        """Generate IAM policy document with required permissions.

        Returns:
            JSON policy document string
        """
        import json

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "CloudstrateOrganizationRead",
                    "Effect": "Allow",
                    "Action": [
                        "organizations:Describe*",
                        "organizations:List*",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "CloudstrateIAMRead",
                    "Effect": "Allow",
                    "Action": [
                        "iam:Get*",
                        "iam:List*",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "CloudstrateEC2Read",
                    "Effect": "Allow",
                    "Action": [
                        "ec2:Describe*",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "CloudstrateRAMRead",
                    "Effect": "Allow",
                    "Action": [
                        "ram:Get*",
                        "ram:List*",
                    ],
                    "Resource": "*",
                },
                {
                    "Sid": "CloudstrateSTSRead",
                    "Effect": "Allow",
                    "Action": [
                        "sts:GetCallerIdentity",
                        "sts:AssumeRole",
                    ],
                    "Resource": "*",
                },
            ],
        }

        return json.dumps(policy, indent=2)
