import json
from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_events as events,
    aws_events_targets as targets,
    Duration,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class CdkInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "CdkInfraQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )
        # VPC
        vpc = ec2.Vpc(self, "VPC")

        # Security Group
        security_group = ec2.SecurityGroup(
            self, "SecurityGroup",
            vpc=vpc,
            description="Allow SSH and HTTP access",
            allow_all_outbound=True
        )
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "Allow SSH")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "Allow HTTP")


        # Network ACL
        network_acl = ec2.NetworkAcl(
            self, "NetworkAcl",
            vpc=vpc,
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )
        # Inbound Rule for SSH
        network_acl.add_entry("SSHInbound",
            rule_number=100,
            traffic=ec2.AclTraffic.tcp_port(22),
            direction=ec2.TrafficDirection.INGRESS,
            network_acl_entry_options=ec2.NetworkAclEntryOptions(
                cidr=ec2.AclCidr.ipv4("0.0.0.0/0"),
                rule_action=ec2.Action.ALLOW
            )
        )

        # Outbound Rule for SSH
        network_acl.add_entry("SSHOutbound",
            rule_number=100,
            traffic=ec2.AclTraffic.all_traffic(),
            direction=ec2.TrafficDirection.EGRESS,
            network_acl_entry_options=ec2.NetworkAclEntryOptions(
                cidr=ec2.AclCidr.ipv4("0.0.0.0/0"),
                rule_action=ec2.Action.ALLOW
            )
        )

        # RDS Instance
        db_instance = rds.DatabaseInstance(
            self, "RDSInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_7
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            security_groups=[security_group],
            allocated_storage=20,
            max_allocated_storage=100,
            database_name="scraperdb",
            credentials=rds.Credentials.from_generated_secret("dbadmin"),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create Key Pair
        key_pair_name = "ec2-key-pair"
        # key_pair = ec2.CfnKeyPair(self, "KeyPair", key_name=key_pair_name)
        # Use the manually created key pair

        # EC2 Instance
        ec2_instance = ec2.Instance(
            self, "EC2Instance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux2(),
            vpc=vpc,
            security_group=security_group,
            key_name=key_pair_name,
            vpc_subnets={
                "subnet_type": ec2.SubnetType.PUBLIC
            },
            associate_public_ip_address=True
        )

        # Wait condition to ensure the instance is fully initialized
        # ec2_instance.instance.add_dependency(key_pair)

        # IAM Role for EC2 Instance
        ec2_instance.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRDSFullAccess")
        )

        # User data script to install dependencies and start the application
        ec2_instance.user_data.add_commands(
            "sudo yum update -y",
            "sudo yum install python3 -y",
            "pip3 install django selenium boto3",
            "cd /home/ec2-user/web-scraper-api/scraper_project",
            "python3 manage.py migrate",
            "python3 manage.py runserver 0.0.0.0:80"
        )

        # Secrets Manager secret for DB credentials
        db_secret = secretsmanager.Secret(self, "DBSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({
                    "username": "dbadmin"
                }),
                generate_string_key="password",
                exclude_characters="\"@/"
            )
        )

        # Lambda function for scraping
        scraper_lambda = _lambda.Function(
            self, "ScraperLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "DB_SECRET_ARN": db_secret.secret_arn,
                "DB_ENDPOINT": db_instance.db_instance_endpoint_address,
                "DB_NAME": "scraperdb",
            }
        )

        # Grant Lambda permissions to read the secret
        db_secret.grant_read(scraper_lambda)

        # CloudWatch Event Rule
        rule = events.Rule(
            self, "ScheduleRule",
            # schedule=events.Schedule.cron(minute="0", hour="0")
            schedule=events.Schedule.rate(Duration.minutes(5))
        )
        rule.add_target(targets.LambdaFunction(scraper_lambda))

        # Grant necessary permissions to the Lambda function
        db_instance.grant_connect(scraper_lambda)

         # Outputs
        CfnOutput(self, "DBEndpoint", value=db_instance.db_instance_endpoint_address, description="The endpoint of the RDS database")
        CfnOutput(self, "DBSecretARN", value=db_secret.secret_arn, description="The ARN of the Secrets Manager secret for DB credentials")
        CfnOutput(self, "EC2InstancePublicDNS", value=ec2_instance.instance_public_dns_name, description="The public DNS of the EC2 instance")
        CfnOutput(self, "KeyPairName", value=key_pair_name, description="The name of the EC2 key pair")
