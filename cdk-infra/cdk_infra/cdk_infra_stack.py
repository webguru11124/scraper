import json
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,  # Import aws_logs for log retention
    Duration,
    RemovalPolicy,
    CfnOutput,
    Duration
)
from constructs import Construct

class CdkInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

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
            vpc_subnets={"subnet_type": ec2.SubnetType.PUBLIC},
            associate_public_ip_address=True
        )

        # IAM Role for EC2 Instance
        ec2_instance.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonRDSFullAccess")
        )

        # User data script to install dependencies, clone the repo, and run the Flask app
        ec2_instance.user_data.add_commands(
            "sudo yum update -y",
            "sudo yum install -y python3 git",
            "pip3 install flask selenium webdriver-manager psycopg2-binary requests boto3 python-dotenv",
            "cd /home/ec2-user",
            "git clone https://github.com/webguru/scraper",
            "cd web-scraper-api",
            "psql -h {} -d scraperdb -U dbadmin -f init_db.sql".format(db_instance.db_instance_endpoint_address),
            "FLASK_APP=app.py flask run --host=0.0.0.0 --port=80"
        )

        # Secrets Manager secret for DB credentials
        db_secret = secretsmanager.Secret(self, "DBSecret",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username": "dbadmin"}),
                generate_string_key="password",
                exclude_characters="\"@/"
            )
        )
        # Create Lambda Layer
        dependency_layer = _lambda.LayerVersion(
            self, "RequestsLayer",
            code=_lambda.Code.from_asset("lambda_layer"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_8],
            description="A layer to include requests library",
        )
        # Lambda function for scraping
        scraper_lambda = _lambda.Function(
            self, "ScraperLambda",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("./lambda"),
            log_retention=logs.RetentionDays.ONE_WEEK,  # Correct log retention setting
            layers=[dependency_layer],  # Add the Lambda Layer
            environment={
                "DB_SECRET_ARN": db_secret.secret_arn,
                "DB_ENDPOINT": db_instance.db_instance_endpoint_address,
                "DB_CLUSTER_ARN": db_instance.instance_arn,
                "DB_NAME": "scraperdb",
                "EC2_INSTANCE_DNS": ec2_instance.instance_public_dns_name,
            },
            vpc=vpc,  # Place Lambda function in the VPC
            timeout=Duration.seconds(900)  # Set timeout to 15 minutes (900 seconds)
        )

        # Grant Lambda permissions to read the secret and connect to the database
        db_secret.grant_read(scraper_lambda)
        db_instance.grant_connect(scraper_lambda)

        # CloudWatch Event Rule
        rule = events.Rule(
            self, "ScheduleRule",
            schedule=events.Schedule.rate(Duration.hours(24))
        )
        rule.add_target(targets.LambdaFunction(scraper_lambda))

        # Outputs
        CfnOutput(self, "DBEndpoint", value=db_instance.db_instance_endpoint_address, description="The endpoint of the RDS database")
        CfnOutput(self, "DBSecretARN", value=db_secret.secret_arn, description="The ARN of the Secrets Manager secret for DB credentials")
        CfnOutput(self, "EC2InstancePublicDNS", value=ec2_instance.instance_public_dns_name, description="The public DNS of the EC2 instance")
        CfnOutput(self, "KeyPairName", value=key_pair_name, description="The name of the EC2 key pair")
