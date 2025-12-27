import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { EnvironmentConfig } from '../config';

export interface FoundationStackProps extends cdk.StackProps {
  config: EnvironmentConfig;
}

/**
 * Foundation Stack - VPC, Security Groups, IAM Roles
 *
 * This stack rarely changes and provides the networking foundation
 * for all other stacks.
 */
export class FoundationStack extends cdk.Stack {
  public readonly vpc: ec2.IVpc;
  public readonly albSecurityGroup: ec2.ISecurityGroup;
  public readonly ecsSecurityGroup: ec2.ISecurityGroup;
  public readonly databaseSecurityGroup: ec2.ISecurityGroup;
  public readonly ecsTaskExecutionRole: iam.IRole;
  public readonly ecsTaskRole: iam.IRole;

  constructor(scope: Construct, id: string, props: FoundationStackProps) {
    super(scope, id, props);

    const { config } = props;
    const prefix = `songwriter-${config.environment}`;

    // =========================================================================
    // VPC
    // =========================================================================
    this.vpc = new ec2.Vpc(this, 'VPC', {
      vpcName: `${prefix}-vpc`,
      ipAddresses: ec2.IpAddresses.cidr(config.vpcCidr),
      maxAzs: 2,
      natGateways: 0, // Save $32/mo - use public subnets with security groups
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          // "Private" subnets that route through IGW (no NAT)
          // Security is enforced via security groups
          name: 'Private',
          subnetType: ec2.SubnetType.PUBLIC, // Actually public for cost savings
          cidrMask: 24,
        },
      ],
    });

    // =========================================================================
    // Security Groups
    // =========================================================================

    // ALB Security Group - allows HTTP/HTTPS from anywhere
    this.albSecurityGroup = new ec2.SecurityGroup(this, 'ALBSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: `${prefix}-alb-sg`,
      description: 'Security group for Application Load Balancer',
      allowAllOutbound: true,
    });
    this.albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'HTTP from anywhere'
    );
    this.albSecurityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'HTTPS from anywhere'
    );

    // ECS Security Group - allows traffic from ALB only
    this.ecsSecurityGroup = new ec2.SecurityGroup(this, 'ECSSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: `${prefix}-ecs-sg`,
      description: 'Security group for ECS tasks',
      allowAllOutbound: true,
    });
    this.ecsSecurityGroup.addIngressRule(
      this.albSecurityGroup,
      ec2.Port.tcp(8081),
      'API from ALB'
    );
    this.ecsSecurityGroup.addIngressRule(
      this.albSecurityGroup,
      ec2.Port.tcp(3000),
      'Web from ALB'
    );
    // Allow ECS tasks to communicate with each other
    this.ecsSecurityGroup.addIngressRule(
      this.ecsSecurityGroup,
      ec2.Port.allTraffic(),
      'Internal ECS communication'
    );

    // Database Security Group - allows traffic from ECS only
    this.databaseSecurityGroup = new ec2.SecurityGroup(this, 'DatabaseSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: `${prefix}-db-sg`,
      description: 'Security group for RDS and ElastiCache',
      allowAllOutbound: true,
    });
    this.databaseSecurityGroup.addIngressRule(
      this.ecsSecurityGroup,
      ec2.Port.tcp(5432),
      'PostgreSQL from ECS'
    );
    this.databaseSecurityGroup.addIngressRule(
      this.ecsSecurityGroup,
      ec2.Port.tcp(6379),
      'Redis from ECS'
    );

    // =========================================================================
    // IAM Roles
    // =========================================================================

    // ECS Task Execution Role - used by ECS to pull images, write logs
    this.ecsTaskExecutionRole = new iam.Role(this, 'ECSTaskExecutionRole', {
      roleName: `${prefix}-ecs-execution-role`,
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          'service-role/AmazonECSTaskExecutionRolePolicy'
        ),
      ],
    });

    // Allow reading secrets from Secrets Manager
    this.ecsTaskExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['secretsmanager:GetSecretValue'],
        resources: [
          `arn:aws:secretsmanager:${this.region}:${this.account}:secret:songwriter/${config.environment}/*`,
        ],
      })
    );

    // ECS Task Role - used by the application itself
    this.ecsTaskRole = new iam.Role(this, 'ECSTaskRole', {
      roleName: `${prefix}-ecs-task-role`,
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // S3 access will be added when we know the bucket name
    // Placeholder policy for now
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject', 's3:ListBucket'],
        resources: [
          `arn:aws:s3:::songwriter-${config.environment}-*`,
          `arn:aws:s3:::songwriter-${config.environment}-*/*`,
        ],
      })
    );

    // Allow ECS Exec for debugging
    this.ecsTaskRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          'ssmmessages:CreateControlChannel',
          'ssmmessages:CreateDataChannel',
          'ssmmessages:OpenControlChannel',
          'ssmmessages:OpenDataChannel',
        ],
        resources: ['*'],
      })
    );

    // =========================================================================
    // Outputs
    // =========================================================================
    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      exportName: `${prefix}-vpc-id`,
    });
  }
}
