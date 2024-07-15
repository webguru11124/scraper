from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
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

        # RDS Instance
        db_instance = rds.DatabaseInstance(
            self, "RDSInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_13_3
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            security_groups=[security_group],
            allocated_storage=20,
            max_allocated_storage=100,
            database_name="scraperdb",
            credentials=rds.Credentials.from_generated_secret("dbadmin"),
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # EC2 Instance
        ec2_instance = ec2.Instance(
            self, "EC2Instance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE2, ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            vpc=vpc,
            security_group=security_group,
        )

        # IAM Role for EC2 Instance
        ec2_instance.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRDSFullAccess")
        )

        # User data script to install Docker and start the application
        ec2_instance.user_data.add_commands(
            "sudo yum update -y",
            "sudo amazon-linux-extras install docker",
            "sudo service docker start",
            "sudo usermod -a -G docker ec2-user",
            "docker run -p 80:80 --name scraper -d my_docker_image"
        )

        # Lambda function for scraping
        scraper_lambda = _lambda.Function(
            self, "ScraperLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "DB_ENDPOINT": db_instance.db_instance_endpoint_address,
                "DB_NAME": "scraperdb",
                "DB_USER": "dbadmin",
                "DB_PASSWORD": db_instance.secret.secret_value.to_string(),
            }
        )

        # CloudWatch Event Rule
        rule = events.Rule(
            self, "ScheduleRule",
            schedule=events.Schedule.cron(minute="0", hour="0")
        )
        rule.add_target(targets.LambdaFunction(scraper_lambda))

        # Grant necessary permissions to the Lambda function
        db_instance.grant_connect(scraper_lambda)
